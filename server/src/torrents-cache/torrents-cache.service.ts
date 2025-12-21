import { Injectable, Logger } from '@nestjs/common';
import { Cron, CronExpression } from '@nestjs/schedule';
import { rm } from 'node:fs/promises';

import { SettingsStore } from 'src/settings/core/settings.store';
import { TorrentsService } from 'src/torrents/torrents.service';
import { TrackerEnum } from 'src/trackers/enum/tracker.enum';

import { TorrentsCacheStore } from './core/torrents-cache.store';

@Injectable()
export class TorrentsCacheService {
  private readonly logger = new Logger(TorrentsCacheService.name);

  constructor(
    private readonly torrentsCacheStore: TorrentsCacheStore,
    private readonly settingsStore: SettingsStore,
    private readonly torrentsService: TorrentsService,
  ) {}

  async deleteAllByTracker(tracker: TrackerEnum) {
    const activeTorrents = await this.torrentsService.getTorrents();

    const imdbDirents = await this.torrentsCacheStore.findImdbDirents();

    for (const imdbDirent of imdbDirents) {
      const isDirectory = imdbDirent.isDirectory();
      if (!isDirectory) continue;

      const trackerDirents = await this.torrentsCacheStore.findTrackerDirents(
        imdbDirent.name,
      );

      for (const trackerDirent of trackerDirents) {
        const isDirectory = trackerDirent.isDirectory();
        const isTargetTracker = trackerDirent.name === tracker.toString();
        if (!isDirectory || !isTargetTracker) continue;

        const trackerDir = this.torrentsCacheStore.buildTrackerDirPath(
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
        await this.torrentsCacheStore.findTrackerDirents(imdbDirent.name);
      const hasTrackerDirs = remainingTrackerDirs.some((dir) =>
        dir.isDirectory(),
      );

      if (!hasTrackerDirs) {
        const trackerDirPath = this.torrentsCacheStore.buildImdbIdDirPath(
          imdbDirent.name,
        );
        await rm(trackerDirPath, { recursive: true, force: true });
      }
    }
  }

  @Cron(CronExpression.EVERY_DAY_AT_5AM)
  async runRetentionCleanup(retentionSeconds?: number) {
    let cacheRetentionSeconds = retentionSeconds ?? null;

    if (cacheRetentionSeconds === null) {
      const setting = await this.settingsStore.findOneOrThrow();
      cacheRetentionSeconds = setting.cacheRetentionSeconds;
    }

    if (cacheRetentionSeconds === null) return;

    const cacheRetentionMs = cacheRetentionSeconds * 1000;

    const activeTorrents = await this.torrentsService.getTorrents();

    const now = Date.now();
    const imdbDirents = await this.torrentsCacheStore.findImdbDirents();

    for (const imdbDirent of imdbDirents) {
      const isDirectory = imdbDirent.isDirectory();
      if (!isDirectory) continue;

      const trackerDirents = await this.torrentsCacheStore.findTrackerDirents(
        imdbDirent.name,
      );

      for (const trackerDirent of trackerDirents) {
        const isDirectory = trackerDirent.isDirectory();
        const isTracker = this.torrentsCacheStore.isTrackerEnum(
          trackerDirent.name,
        );
        if (!isDirectory || !isTracker) continue;

        const tracker = trackerDirent.name as TrackerEnum;
        const trackerDir = this.torrentsCacheStore.buildTrackerDirPath(
          imdbDirent.name,
          tracker,
        );

        const lastUsedMs =
          await this.torrentsCacheStore.getMarkerTime(trackerDir);

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
        await this.torrentsCacheStore.findTrackerDirents(imdbDirent.name);
      const hasTrackerDirs = remainingTrackerDirs.some((dir) =>
        dir.isDirectory(),
      );

      if (!hasTrackerDirs) {
        const trackerDirPath = this.torrentsCacheStore.buildImdbIdDirPath(
          imdbDirent.name,
        );
        await rm(trackerDirPath, { recursive: true, force: true });
      }
    }
  }
}
