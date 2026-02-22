import { Injectable, Logger, OnModuleInit } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { isArray } from 'lodash';
import { mkdir, rm, stat, utimes, writeFile } from 'node:fs/promises';
import { join } from 'node:path';

import { safeReadFile, safeReaddir } from 'src/common/utils/file.util';
import { parseTorrent } from 'src/common/utils/parse-torrent.util';
import { TrackerEnum } from 'src/trackers/enum/tracker.enum';

import { TorrentCacheId } from '../type/torrent-cache-id.type';
import { TorrentCacheToCreate } from '../type/torrent-cache-to-create.type';
import { TorrentCache } from '../type/torrent-cache.type';
import { TorrentInfo } from '../type/torrent-info.type';

@Injectable()
export class TorrentsCacheStore implements OnModuleInit {
  private readonly logger = new Logger(TorrentsCacheStore.name);
  private readonly torrentsDir: string;

  constructor(private readonly configService: ConfigService) {
    this.torrentsDir = this.configService.getOrThrow<string>(
      'torrent.torrents-dir',
    );
  }

  async onModuleInit() {
    await mkdir(this.torrentsDir, { recursive: true });
  }

  async create(payload: TorrentCacheToCreate): Promise<TorrentCache> {
    const { tracker, torrentId, torrentBuffer } = payload;

    const trackerDirPath = this.buildTrackerDirPath(tracker);
    await mkdir(trackerDirPath, { recursive: true });
    await this.touchMarker(trackerDirPath);

    const torrentFilePath = this.buildTorrentFilePath(tracker, torrentId);

    await writeFile(torrentFilePath, torrentBuffer);
    const torrentFile = parseTorrent(torrentBuffer);

    this.logger.log(`💾 Torrent mentésre került: ${torrentFile.name}`);

    return {
      ...payload,
      torrentFilePath: torrentFilePath,
      info: torrentFile,
    };
  }

  async findByTorrentId(
    tracker: TrackerEnum,
    torrentIds: string[],
  ): Promise<TorrentCache[]> {
    const parsedTorrents: TorrentCache[] = [];

    for (const torrentId of torrentIds) {
      const path = this.buildTorrentFilePath(tracker, torrentId);
      const torrentInfo = await this.fileToParseTorrent(path);

      if (!torrentInfo) continue;

      parsedTorrents.push({
        tracker,
        torrentId,
        torrentFilePath: path,
        info: torrentInfo,
      });
    }

    return parsedTorrents;
  }

  async findOne(payload: TorrentCacheId): Promise<TorrentCache | null> {
    const torrentFilePath = this.buildTorrentFilePath(
      payload.tracker,
      payload.torrentId,
    );

    const torrentInfo = await this.fileToParseTorrent(torrentFilePath);

    if (!torrentInfo) {
      return null;
    }

    return {
      ...payload,
      torrentFilePath: torrentFilePath,
      info: torrentInfo,
    };
  }

  async delete(paths: string[] | string): Promise<void> {
    if (isArray(paths)) {
      await Promise.all(paths.map((path) => rm(path, { force: true })));
    } else {
      await rm(paths, { force: true });
    }
  }

  async findTrackerDirents() {
    const dirents = await safeReaddir(this.torrentsDir);
    return dirents;
  }

  async findTorrentDirents(tracker: TrackerEnum) {
    const trackerDir = this.buildTrackerDirPath(tracker);
    const dirents = await safeReaddir(trackerDir);
    return dirents;
  }

  isTorrentFile(fileName: string): boolean {
    return fileName.toLowerCase().endsWith('.torrent');
  }

  buildTrackerDirPath(tracker: TrackerEnum) {
    return join(this.torrentsDir, tracker);
  }

  private buildTorrentFilePath(tracker: TrackerEnum, torrentId: string) {
    const trackerDirPath = this.buildTrackerDirPath(tracker);
    return join(trackerDirPath, `${torrentId}.torrent`);
  }

  private async fileToParseTorrent(
    torrentPath: string,
  ): Promise<TorrentInfo | null> {
    const fileBuffer = await safeReadFile(torrentPath);

    if (!fileBuffer) return null;

    await this.touchMarker(torrentPath);
    const parsedTorrent = parseTorrent(fileBuffer);
    return parsedTorrent;
  }

  async getMarkerTime(torrentPath: string) {
    try {
      const st = await stat(torrentPath);
      return st.mtimeMs;
    } catch {
      const fallbackMs: number = new Date(0).getTime();
      return fallbackMs;
    }
  }

  private async touchMarker(torrentPath: string) {
    const date = new Date();
    await utimes(torrentPath, date, date);
  }
}
