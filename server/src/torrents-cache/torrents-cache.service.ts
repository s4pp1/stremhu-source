import { Injectable, Logger } from '@nestjs/common';
import { Cron, CronExpression } from '@nestjs/schedule';
import { rm } from 'node:fs/promises';
import { join } from 'node:path';

import { SettingsCoreService } from 'src/settings/core/settings-core.service';
import { TorrentsService } from 'src/torrents/torrents.service';
import { TrackerEnum } from 'src/trackers/enum/tracker.enum';
import { isTrackerEnum } from 'src/trackers/util/is-tracker-enum';

import { TorrentsCacheStore } from './core/torrents-cache.store';

@Injectable()
export class TorrentsCacheService {
  private readonly logger = new Logger(TorrentsCacheService.name);

  constructor(
    private readonly torrentsCacheStore: TorrentsCacheStore,
    private readonly settingsCoreService: SettingsCoreService,
    private readonly torrentsService: TorrentsService,
  ) {}

  async deleteAllByTracker(tracker: TrackerEnum) {
    const activeTorrents = await this.torrentsService.find();

    const trackerDirents = await this.torrentsCacheStore.findTrackerDirents();

    for (const trackerDirent of trackerDirents) {
      const isDirectory = trackerDirent.isDirectory();
      const isTargetTracker = trackerDirent.name === tracker.toString();
      if (!isDirectory || !isTargetTracker) continue;

      const trackerDir = this.torrentsCacheStore.buildTrackerDirPath(tracker);

      const hasRunTorrent = activeTorrents.some(
        (activeTorrent) =>
          activeTorrent.tracker.toString() === trackerDirent.name,
      );

      if (!hasRunTorrent) {
        await rm(trackerDir, { recursive: true, force: true });
      }
    }
  }

  @Cron(CronExpression.EVERY_DAY_AT_5AM)
  async runRetentionCleanup(retentionSeconds?: number) {
    let cacheRetentionSeconds = retentionSeconds ?? null;

    if (cacheRetentionSeconds === null) {
      const setting = await this.settingsCoreService.appSettings();

      if (setting.cacheRetentionSeconds > 0) {
        cacheRetentionSeconds = setting.cacheRetentionSeconds;
      }
    }

    if (cacheRetentionSeconds === null) return;

    const cacheRetentionMs = cacheRetentionSeconds * 1000;

    const activeTorrents = await this.torrentsService.find();

    const now = Date.now();

    const trackerDirents = await this.torrentsCacheStore.findTrackerDirents();

    for (const trackerDirent of trackerDirents) {
      const isDirectory = trackerDirent.isDirectory();
      const isTracker = isTrackerEnum(trackerDirent.name);

      if (!isDirectory || !isTracker) {
        const deleteblePath = join(
          trackerDirent.parentPath,
          trackerDirent.name,
        );
        await rm(deleteblePath, { recursive: true, force: true });
        this.logger.log(`🧹 Ismeretlen mappa/file törölve: ${deleteblePath}`);

        continue;
      }

      const tracker = trackerDirent.name as TrackerEnum;

      const torrentDirents =
        await this.torrentsCacheStore.findTorrentDirents(tracker);

      for (const torrentDirent of torrentDirents) {
        const isDirectory = torrentDirent.isDirectory();
        const torrentPath = join(torrentDirent.parentPath, torrentDirent.name);

        if (isDirectory) {
          await rm(torrentPath, { recursive: true, force: true });
          this.logger.log(`🧹 Ismeretlen mappa törölve: ${torrentPath}`);
          continue;
        }

        const isTorrent = this.torrentsCacheStore.isTorrentFile(
          torrentDirent.name,
        );

        if (!isTorrent) {
          await rm(torrentPath, { recursive: true, force: true });
          this.logger.log(`🧹 Ismeretlen file törölve: ${torrentPath}`);
          continue;
        }

        const lastUsedMs =
          await this.torrentsCacheStore.getMarkerTime(torrentPath);

        const hasRunTorrent = activeTorrents.some(
          (activeTorrent) =>
            activeTorrent.tracker.toString() === trackerDirent.name &&
            `${activeTorrent.torrentId}.torrent` === torrentDirent.name,
        );

        if (!hasRunTorrent && now - lastUsedMs > cacheRetentionMs) {
          await rm(torrentPath, { recursive: true, force: true });
          this.logger.log(`🧹 Törölve inaktív torrent cache: ${torrentPath}`);
        }
      }
    }
  }
}
