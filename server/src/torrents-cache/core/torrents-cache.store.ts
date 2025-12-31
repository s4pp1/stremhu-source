import { Injectable, Logger, OnModuleInit } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import _ from 'lodash';
import { Dirent } from 'node:fs';
import { mkdir, rm, stat, utimes, writeFile } from 'node:fs/promises';
import { join } from 'node:path';

import { safeReadFile, safeReaddir } from 'src/common/utils/file.util';
import {
  ParsedTorrent,
  parseTorrent,
  toTorrentFile,
} from 'src/common/utils/parse-torrent.util';
import { TrackerEnum } from 'src/trackers/enum/tracker.enum';

import { MARKER_FILENAME } from '../torrents-cache.constants';
import {
  ParsedTorrentPath,
  TorrentCache,
  TorrentCacheId,
  TorrentsCache,
} from '../torrents-cache.types';
import { TorrentCacheToCreate } from '../type/torrent-cache-to-create.type';

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
    const { imdbId, tracker, torrentId, parsed } = payload;

    const trackerDirPath = this.buildTrackerDirPath(imdbId, tracker);
    await mkdir(trackerDirPath, { recursive: true });
    await this.touchMarker(trackerDirPath);

    const torrentFilePath = this.buildTorrentFilePath(
      imdbId,
      tracker,
      torrentId,
    );

    const torrentFile = await toTorrentFile(parsed);

    await writeFile(torrentFilePath, torrentFile);

    this.logger.log(`💾 Torrent mentésre került: ${parsed.name}`);

    return {
      ...payload,
      torrentFilePath: torrentFilePath,
    };
  }

  async find(payload: TorrentsCache): Promise<TorrentCache[]> {
    const { imdbId, tracker } = payload;

    const trackerDirPath = this.buildTrackerDirPath(imdbId, tracker);
    const torrentDirents = await this.getTorrentDirents(trackerDirPath);

    if (torrentDirents.length !== 0) {
      await this.touchMarker(trackerDirPath);
    }

    const parsedTorrents: TorrentCache[] = [];

    for (const torrentDirent of torrentDirents) {
      const [torrentId] = torrentDirent.name.split('.');

      const path = join(trackerDirPath, torrentDirent.name);
      const parsed = await this.fileToParseTorrent(path);

      if (!parsed) {
        this.logger.error(`🚨 A(z) "${path}" nem található.`);
        continue;
      }

      parsedTorrents.push({
        ...payload,
        torrentId,
        torrentFilePath: path,
        parsed,
      });
    }

    return parsedTorrents;
  }

  async findOne(payload: TorrentCacheId): Promise<TorrentCache | null> {
    const torrentFilePath = this.buildTorrentFilePath(
      payload.imdbId,
      payload.tracker,
      payload.torrentId,
    );

    const parsed = await this.fileToParseTorrent(torrentFilePath);

    if (!parsed) {
      return null;
    }

    return {
      ...payload,
      torrentFilePath: torrentFilePath,
      parsed,
    };
  }

  async delete(paths: string[] | string): Promise<void> {
    if (_.isArray(paths)) {
      await Promise.all(paths.map((path) => rm(path, { force: true })));
    } else {
      await rm(paths, { force: true });
    }
  }

  async findImdbDirents() {
    const dirents = await safeReaddir(this.torrentsDir);
    return dirents;
  }

  async findTrackerDirents(imdbId: string) {
    const trackerDir = join(this.torrentsDir, imdbId);
    const dirents = await safeReaddir(trackerDir);
    return dirents;
  }

  isTrackerEnum(value: string) {
    return Object.values(TrackerEnum).includes(value as TrackerEnum);
  }

  private async getTorrentDirents(trackerDir: string): Promise<Dirent[]> {
    const dirents = await safeReaddir(trackerDir);
    const torrentDirents = dirents.filter((dirents) => {
      const isFile = dirents.isFile();
      const isTorrent = dirents.name.toLowerCase().endsWith('.torrent');
      return isFile && isTorrent;
    });
    return torrentDirents;
  }

  buildImdbIdDirPath(imdbId: string): string {
    return join(this.torrentsDir, imdbId);
  }

  buildTrackerDirPath(imdbId: string, tracker: TrackerEnum) {
    const imdbIdDirPath = this.buildImdbIdDirPath(imdbId);
    return join(imdbIdDirPath, tracker);
  }

  private buildTorrentFilePath(
    imdbId: string,
    tracker: TrackerEnum,
    torrentId: string,
  ) {
    const trackerDirPath = this.buildTrackerDirPath(imdbId, tracker);
    return join(trackerDirPath, `${torrentId}.torrent`);
  }

  private async fileToParseTorrent(
    torrentPath: string,
  ): Promise<ParsedTorrent | null> {
    const fileBuffer = await safeReadFile(torrentPath);

    if (!fileBuffer) {
      return null;
    }

    const parsedTorrent = await parseTorrent(new Uint8Array(fileBuffer));
    return parsedTorrent;
  }

  private parseTorrentPath(fullPath: string): ParsedTorrentPath {
    const path = fullPath.replace(this.torrentsDir, '');
    const [imdbId, tracker, details] = path.split('/');
    const [torrentId] = details.split('.');
    return { imdbId, tracker: tracker as TrackerEnum, torrentId };
  }

  async getMarkerTime(trackerDir: string) {
    try {
      const markerPath = join(trackerDir, MARKER_FILENAME);
      const st = await stat(markerPath);
      return st.mtimeMs;
    } catch {
      const fallbackMs: number = new Date(0).getTime();
      return fallbackMs;
    }
  }

  private async touchMarker(trackerTorrentsDir: string) {
    const date = new Date();
    const markerPath = join(trackerTorrentsDir, MARKER_FILENAME);
    await writeFile(markerPath, '', { flag: 'a' });
    await utimes(markerPath, date, date);
  }
}
