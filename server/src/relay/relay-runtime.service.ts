import {
  Injectable,
  Logger,
  OnApplicationBootstrap,
  OnApplicationShutdown,
} from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { mkdir } from 'node:fs/promises';

import { RelayService } from 'src/relay/relay.service';
import { PersistedTorrentsService } from 'src/torrents/persisted/persisted-torrents.service';
import { TrackersStore } from 'src/trackers/core/trackers.store';
import { TrackerDiscoveryService } from 'src/trackers/tracker-discovery.service';

@Injectable()
export class RelayRuntimeService
  implements OnApplicationBootstrap, OnApplicationShutdown
{
  private readonly logger = new Logger(RelayRuntimeService.name);

  private readonly downloadsDir: string;

  constructor(
    private readonly configService: ConfigService,
    private readonly persistedTorrentsService: PersistedTorrentsService,
    private readonly relayService: RelayService,
    private readonly trackersStore: TrackersStore,
    private readonly trackerDiscoveryService: TrackerDiscoveryService,
  ) {
    this.downloadsDir = this.configService.getOrThrow<string>(
      'torrent.downloads-dir',
    );
  }

  async onApplicationBootstrap() {
    // Downloads mappa létrehozása, ha nem létezik
    await mkdir(this.downloadsDir, { recursive: true });

    // Torrent kliens elindítása
    await this.relayService.bootstrap();

    // Torrentek lekérése és visszarakása a kliensbe
    const persistedTorrents = await this.persistedTorrentsService.find();

    // Tracker-ek letöltése
    const trackers = await this.trackersStore.find();

    for (const persistedTorrent of persistedTorrents) {
      const torrentCache = await this.trackerDiscoveryService.findOneByTracker(
        persistedTorrent.tracker,
        persistedTorrent.torrentId,
      );

      if (!torrentCache) {
        this.logger.error(
          `🚨 "${persistedTorrent.infoHash}" nem tölthető vissza.`,
        );
        await this.persistedTorrentsService.deleteByInfoHash(
          persistedTorrent.infoHash,
        );
        continue;
      }

      const tracker = trackers.find(
        (tracker) => tracker.tracker === persistedTorrent.tracker,
      );

      let downloadFullTorrent = tracker?.downloadFullTorrent ?? false;

      if (persistedTorrent.fullDownload !== null) {
        downloadFullTorrent = persistedTorrent.fullDownload;
      }

      this.relayService
        .addTorrentWithChecking({
          torrentFilePath: torrentCache.torrentFilePath,
          downloadFullTorrent: downloadFullTorrent,
        })
        .then((relayTorrent) => {
          this.logger.log(`🔼 .torrent fájl betöltve: ${relayTorrent.name}`);
        })
        .catch(() => {
          this.logger.error(
            `🚨 .torrent fájl betöltése közben hiba történt: ${torrentCache.tracker} - ${torrentCache.torrentId}`,
          );
        });
    }
  }

  async onApplicationShutdown(signal?: string) {
    this.logger.log(`🛑 Torrent kliens leállítása... signal: ${signal}`);

    // A futás óta feltöltött tartalom mennyiségének tárolása
    const relayTorrents = await this.relayService.getTorrents();

    await Promise.all(
      relayTorrents.map(async (relayTorrent) => {
        const persistedTorrent =
          await this.persistedTorrentsService.findOneByInfoHashOrThrow(
            relayTorrent.infoHash,
          );

        const uploaded = persistedTorrent.uploaded + relayTorrent.uploaded;

        await this.persistedTorrentsService.updateOne(
          relayTorrent.infoHash,
          {
            uploaded,
          },
          persistedTorrent,
        );
      }),
    );

    // Torrent kliens leállítása
    await this.relayService.shutdown();
  }
}
