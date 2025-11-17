import { Injectable, Logger, OnApplicationBootstrap } from '@nestjs/common';
import { Cron, CronExpression, SchedulerRegistry } from '@nestjs/schedule';
import ms from 'ms';
import { rm } from 'node:fs/promises';

import { SettingsStore } from 'src/settings/core/settings.store';
import { TrackerEnum } from 'src/trackers/enums/tracker.enum';
import { WebTorrentService } from 'src/web-torrent/web-torrent.service';

import { TorrentCacheStore } from './core/torrent-cache.store';

@Injectable()
export class TorrentCacheService implements OnApplicationBootstrap {
  private readonly logger = new Logger(TorrentCacheService.name);

  constructor(
    private readonly schedulerRegistry: SchedulerRegistry,
    private readonly torrentCacheStore: TorrentCacheStore,
    private settingsStore: SettingsStore,
    private webTorrentService: WebTorrentService,
  ) {}

  async onApplicationBootstrap() {
    const setting = await this.settingsStore.findOneOrThrow();
    const job = this.schedulerRegistry.getCronJob('retentionCleanup');

    if (!setting.cacheRetention) {
      await job.stop();
    }
  }

  async setRetentionCleanupCron(enabled: boolean) {
    const job = this.schedulerRegistry.getCronJob('retentionCleanup');

    if (enabled && !job.isActive) {
      job.start();
    }

    if (!enabled && job.isActive) {
      await job.stop();
    }
  }

  async deleteAllByTracker(tracker: TrackerEnum) {
    const activeTorrents = await this.webTorrentService.getTorrents();

    const imdbDirents = await this.torrentCacheStore.findImdbDirents();

    for (const imdbDirent of imdbDirents) {
      const isDirectory = imdbDirent.isDirectory();
      if (!isDirectory) continue;

      const trackerDirents = await this.torrentCacheStore.findTrackerDirents(
        imdbDirent.name,
      );

      for (const trackerDirent of trackerDirents) {
        const isDirectory = trackerDirent.isDirectory();
        const isTargetTracker = trackerDirent.name === tracker.toString();
        if (!isDirectory || !isTargetTracker) continue;

        const trackerDir = this.torrentCacheStore.buildTrackerDirPath(
          imdbDirent.name,
          tracker,
        );

        const hasRunTorrent = activeTorrents.some(
          (activeTorrent) =>
            activeTorrent.imdbId === imdbDirent.name &&
            activeTorrent.tracker.toString() === trackerDirent.name,
        );

        if (!hasRunTorrent) {
          await rm(trackerDir, { recursive: true, force: true });
        }
      }

      const remainingTrackerDirs =
        await this.torrentCacheStore.findTrackerDirents(imdbDirent.name);
      const hasTrackerDirs = remainingTrackerDirs.some((dir) =>
        dir.isDirectory(),
      );

      if (!hasTrackerDirs) {
        const trackerDirPath = this.torrentCacheStore.buildImdbIdDirPath(
          imdbDirent.name,
        );
        await rm(trackerDirPath, { recursive: true, force: true });
      }
    }
  }

  @Cron(CronExpression.EVERY_DAY_AT_5AM, { name: 'retentionCleanup' })
  async runRetentionCleanup() {
    const { cacheRetention } = await this.settingsStore.findOneOrThrow();
    if (!cacheRetention) return;

    const cacheRetentionMs = ms(cacheRetention as ms.StringValue);

    const activeTorrents = await this.webTorrentService.getTorrents();

    const now = Date.now();
    const imdbDirents = await this.torrentCacheStore.findImdbDirents();

    for (const imdbDirent of imdbDirents) {
      const isDirectory = imdbDirent.isDirectory();
      if (!isDirectory) continue;

      const trackerDirents = await this.torrentCacheStore.findTrackerDirents(
        imdbDirent.name,
      );

      for (const trackerDirent of trackerDirents) {
        const isDirectory = trackerDirent.isDirectory();
        const isTracker = this.torrentCacheStore.isTrackerEnum(
          trackerDirent.name,
        );
        if (!isDirectory || !isTracker) continue;

        const tracker = trackerDirent.name as TrackerEnum;
        const trackerDir = this.torrentCacheStore.buildTrackerDirPath(
          imdbDirent.name,
          tracker,
        );

        const lastUsedMs =
          await this.torrentCacheStore.getMarkerTime(trackerDir);

        const hasRunTorrent = activeTorrents.some(
          (activeTorrent) =>
            activeTorrent.imdbId === imdbDirent.name &&
            activeTorrent.tracker.toString() === trackerDirent.name,
        );

        if (!hasRunTorrent && now - lastUsedMs > cacheRetentionMs) {
          await rm(trackerDir, { recursive: true, force: true });
          this.logger.log(`🧹 Törölve inaktív torrent cache: ${trackerDir}`);
        }
      }

      const remainingTrackerDirs =
        await this.torrentCacheStore.findTrackerDirents(imdbDirent.name);
      const hasTrackerDirs = remainingTrackerDirs.some((dir) =>
        dir.isDirectory(),
      );

      if (!hasTrackerDirs) {
        const trackerDirPath = this.torrentCacheStore.buildImdbIdDirPath(
          imdbDirent.name,
        );
        await rm(trackerDirPath, { recursive: true, force: true });
      }
    }
  }
}
