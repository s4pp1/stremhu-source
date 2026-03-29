import {
  Injectable,
  Logger,
  OnApplicationBootstrap,
  OnApplicationShutdown,
} from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { difference } from 'lodash';
import { mkdir } from 'node:fs/promises';

import { RelayRuntimeService } from 'src/relay/relay-runtime.service';
import { RelayService } from 'src/relay/relay.service';
import { RelayStatus } from 'src/relay/type/relay-status.enum';
import { RelaySettingsService } from 'src/settings/relay/relay-settings.service';
import { PersistedTorrentsService } from 'src/torrents/persisted/persisted-torrents.service';
import { TrackersStore } from 'src/trackers/core/trackers.store';
import { TrackerDiscoveryService } from 'src/trackers/tracker-discovery.service';
import { TrackerTorrentFound } from 'src/trackers/type/tracker-torrent-found.type';

@Injectable()
export class RelaySyncService
  implements OnApplicationBootstrap, OnApplicationShutdown
{
  private readonly logger = new Logger(RelaySyncService.name);

  private readonly downloadsDir: string;
  private currentRelayStatus: RelayStatus = RelayStatus.INITIALIZING;
  private lastUploadedValues = new Map<string, number>();
  private uploadSyncInterval: NodeJS.Timeout | null = null;

  constructor(
    private readonly configService: ConfigService,
    private readonly persistedTorrentsService: PersistedTorrentsService,
    private readonly relayService: RelayService,
    private readonly relayRuntimeService: RelayRuntimeService,
    private readonly relaySettingsService: RelaySettingsService,
    private readonly trackersStore: TrackersStore,
    private readonly trackerDiscoveryService: TrackerDiscoveryService,
  ) {
    this.downloadsDir = this.configService.getOrThrow<string>(
      'torrent.downloads-dir',
    );
  }

  async onApplicationBootstrap() {
    await mkdir(this.downloadsDir, { recursive: true });

    this.relayRuntimeService.getStatus$().subscribe((status) => {
      this.currentRelayStatus = status;

      if (status === RelayStatus.ONLINE) {
        void this.onRelayOnline();
      }
    });

    this.uploadSyncInterval = setInterval(() => {
      void this.syncUploadStats();
    }, 60000);

    void this.relayRuntimeService.bootstrap();
  }

  async onApplicationShutdown(signal?: string) {
    if (this.uploadSyncInterval) {
      clearInterval(this.uploadSyncInterval);
      this.uploadSyncInterval = null;
    }

    this.logger.log(`🛑 Torrent kliens leállítása... signal: ${signal}`);

    try {
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
            { uploaded },
            persistedTorrent,
          );
        }),
      );
    } catch {
      await this.flushUploadedStatsToDB();
    }

    await this.relayRuntimeService.shutdown();
  }

  private async onRelayOnline() {
    await this.flushUploadedStatsToDB();
    await this.syncSettings();
    await this.syncTorrents();
  }

  private async syncUploadStats() {
    if (this.currentRelayStatus !== RelayStatus.ONLINE) return;

    try {
      const relayTorrents = await this.relayService.getTorrents();

      for (const relayTorrent of relayTorrents) {
        this.lastUploadedValues.set(
          relayTorrent.infoHash,
          relayTorrent.uploaded,
        );
      }

      const uploadedInfoHashes = [...this.lastUploadedValues.keys()];
      const torrentInfoHashes = relayTorrents.map(
        (torrent) => torrent.infoHash,
      );

      const removedInfoHashes = difference(
        uploadedInfoHashes,
        torrentInfoHashes,
      );

      for (const infoHash of removedInfoHashes) {
        this.lastUploadedValues.delete(infoHash);
      }
    } catch (error) {
      this.logger.warn(
        `🚨 Feltöltési statisztikák lekérése közben hiba történt`,
        error,
      );
    }
  }

  private async flushUploadedStatsToDB() {
    const uploadedStats = this.lastUploadedValues.entries();

    for (const [infoHash, uploaded] of uploadedStats) {
      try {
        const persistedTorrent =
          await this.persistedTorrentsService.findOneByInfoHash(infoHash);

        if (!persistedTorrent) continue;

        await this.persistedTorrentsService.updateOne(
          infoHash,
          { uploaded: persistedTorrent.uploaded + uploaded },
          persistedTorrent,
        );
      } catch (error) {
        this.logger.warn(
          `🚨 Feltöltési statisztikák szinkronizálása közben hiba történt: ${infoHash}`,
          error,
        );
      }
    }

    this.lastUploadedValues.clear();
  }

  private async syncSettings() {
    try {
      this.logger.log('⚙️ Beállítások szinkronizálása a Relay-be...');

      const port = this.configService.getOrThrow<number>('torrent.port');
      const setting = await this.relaySettingsService.get();

      await this.relayService.updateConfig({ ...setting, port });

      this.logger.log('✅ Relay beállítások szinkronizálva.');
    } catch (err) {
      this.logger.error(
        '🚨 Nem sikerült szinkronizálni a Relay beállításokat!',
        err,
      );
    }
  }

  private async syncTorrents() {
    this.logger.log('🔄 Torrentek szinkronizálása a Relay-be...');

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

      void this.syncTorrent(torrentCache, downloadFullTorrent);
    }
  }

  private async syncTorrent(
    torrentCache: TrackerTorrentFound,
    downloadFullTorrent: boolean,
  ) {
    try {
      await this.relayService.addTorrent({
        torrentFilePath: torrentCache.torrentFilePath,
        downloadFullTorrent,
      });
    } catch (error) {
      this.logger.error(
        `🚨 .torrent fájl betöltése közben hiba történt: ${torrentCache.tracker} - ${torrentCache.torrentId}`,
        error,
      );
    }
  }
}
