import {
  Injectable,
  Logger,
  OnApplicationBootstrap,
  OnApplicationShutdown,
} from '@nestjs/common';
import { ConfigService } from '@nestjs/config';

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

  constructor(
    private readonly configService: ConfigService,
    private readonly persistedTorrentsService: PersistedTorrentsService,
    private readonly relayService: RelayService,
    private readonly relayRuntimeService: RelayRuntimeService,
    private readonly relaySettingsService: RelaySettingsService,
    private readonly trackersStore: TrackersStore,
    private readonly trackerDiscoveryService: TrackerDiscoveryService,
  ) {}

  onApplicationBootstrap() {
    this.relayRuntimeService.getStatus$().subscribe((status) => {
      if (status === RelayStatus.ONLINE) {
        void this.onRelayOnline();
      }
    });

    void this.relayRuntimeService.bootstrap();
  }

  async onApplicationShutdown(signal?: string) {
    this.logger.log(`🛑 Relay leállítása... signal: ${signal}`);
    await this.relayRuntimeService.shutdown();
    this.logger.log('✅ Relay leállítva.');
  }

  private async onRelayOnline() {
    await this.syncSettings();
    await this.syncTorrents();

    this.logger.log('✅ Relay szinkronizáció és konfiguráció befejezve.');
  }

  private async syncSettings() {
    try {
      const port = this.configService.getOrThrow<number>('torrent.port');
      const setting = await this.relaySettingsService.get();

      await this.relayService.updateConfig({ ...setting, port });
    } catch (err) {
      this.logger.error('🚨 Relay szinkronizáció sikertelen!', err);
    }
  }

  private async syncTorrents() {
    const persistedTorrents = await this.persistedTorrentsService.find();
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
