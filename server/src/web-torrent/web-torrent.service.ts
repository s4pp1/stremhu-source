import {
  Injectable,
  Logger,
  NotFoundException,
  OnApplicationBootstrap,
  OnApplicationShutdown,
} from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { mkdir, rm } from 'node:fs/promises';
import path from 'node:path';
import { In, Not } from 'typeorm';
import type { Torrent, TorrentFile } from 'webtorrent';

import { SettingsStore } from 'src/settings/core/settings.store';
import { TorrentCacheStore } from 'src/torrent-cache/core/torrent-cache.store';
import { TrackerEnum } from 'src/trackers/enums/tracker.enum';

import { WebTorrentRunsService } from './runs/web-torrent-runs.service';
import { ActiveTorrent, WebTorrentToAdd } from './web-torrent.types';

@Injectable()
export class WebTorrentService
  implements OnApplicationBootstrap, OnApplicationShutdown
{
  private readonly logger = new Logger(WebTorrentService.name);
  private readonly downloadsDir: string;

  private client: import('webtorrent').Instance;

  constructor(
    private configService: ConfigService,
    private webTorrentRunsService: WebTorrentRunsService,
    private torrentCacheStore: TorrentCacheStore,
    private settingsStore: SettingsStore,
  ) {
    this.downloadsDir = this.configService.getOrThrow<string>(
      'web-torrent.downloads-dir',
    );
  }

  async onApplicationBootstrap() {
    await mkdir(this.downloadsDir, { recursive: true });

    const setting = await this.settingsStore.findOneOrThrow();

    const { default: WebTorrent } = await import('webtorrent');

    this.client = new WebTorrent({
      utp: true,
      dht: false,
      webSeeds: false,
      lsd: false,
      torrentPort: this.configService.getOrThrow<number>('web-torrent.port'),
      uploadLimit: setting.uploadLimit,
    });

    this.logger.log('✅ WebTorrent kliens elindult');

    const runTorrents = await this.webTorrentRunsService.find();

    for (const runTorrent of runTorrents) {
      const torrentCache = await this.torrentCacheStore.findOne({
        tracker: runTorrent.tracker,
        torrentId: runTorrent.torrentId,
        imdbId: runTorrent.imdbId,
      });

      if (!torrentCache) {
        this.logger.error(
          `A torrent nem tölthető vissza: ${runTorrent.infoHash}`,
        );
        await this.webTorrentRunsService.delete(runTorrent.infoHash);
        continue;
      }

      this.client.add(
        torrentCache.parsed,
        { path: this.downloadsDir, storeCacheSlots: 0 },
        (torrent) => {
          this.logger.log(`🔼 .torrent fájl betöltve: ${torrent.name}`);

          torrent.deselect(0, torrent.pieces.length - 1, 0);
        },
      );
    }

    this.client.on('error', (err) => {
      this.logger.error('⚠️ WebTorrent hiba:', err);
    });
  }

  async onApplicationShutdown(signal?: string) {
    this.logger.log(`🛑 WebTorrent kliens leállítása... signal: ${signal}`);

    const { torrents } = this.client;

    await Promise.all(
      torrents.map((torrent) =>
        this.webTorrentRunsService.flushUpload(
          torrent.infoHash,
          torrent.uploaded,
        ),
      ),
    );

    await new Promise<void>((resolve) => {
      this.client.destroy(() => {
        this.logger.log('✅ WebTorrent kliens leállítva.');
        resolve();
      });
    });
  }

  async getTorrents(): Promise<ActiveTorrent[]> {
    const webTorrentRuns = await this.webTorrentRunsService.find();

    const { torrents } = this.client;

    const activeTorrents: ActiveTorrent[] = [];

    for (const torrent of torrents) {
      const webTorrentRun = webTorrentRuns.find(
        (webTorrentRun) => webTorrentRun.infoHash === torrent.infoHash,
      );

      if (!webTorrentRun) {
        await this.delete(torrent.infoHash);
        continue;
      }

      const activeTorrent: ActiveTorrent = {
        name: torrent.name,
        imdbId: webTorrentRun.imdbId,
        tracker: webTorrentRun.tracker,
        torrentId: webTorrentRun.torrentId,
        infoHash: torrent.infoHash,
        downloaded: torrent.downloaded,
        progress: torrent.progress,
        total: torrent.length,
        uploaded: torrent.uploaded + webTorrentRun.uploaded,
        uploadSpeed: torrent.uploadSpeed,
      };

      activeTorrents.push(activeTorrent);
    }

    return activeTorrents;
  }

  async getTorrent(infoHash: string): Promise<Torrent | null> {
    const torrent = await this.client.get(infoHash);

    return torrent || null;
  }

  async addTorrent(payload: WebTorrentToAdd): Promise<Torrent> {
    const { parsed, ...rest } = payload;

    return new Promise((resolve, reject) => {
      const torrent = this.client.add(
        parsed,
        { path: this.downloadsDir, storeCacheSlots: 0 },
        async (torrent) => {
          torrent.deselect(0, torrent.pieces.length - 1, 0);
          await this.webTorrentRunsService.create({
            ...rest,
            infoHash: torrent.infoHash,
          });
          this.logger.log(`🎬 Torrent a WebTorrent-hez adva: ${torrent.name}`);
          resolve(torrent);
        },
      );
      torrent.once('error', reject);
    });
  }

  getFileByIndex(torrent: Torrent, fileIdx: number): TorrentFile {
    if (!torrent.files[fileIdx]) {
      throw new Error(
        `Nincs ilyen fileIdx: ${fileIdx}. Fájlok száma: ${torrent.files.length}`,
      );
    }
    return torrent.files[fileIdx];
  }

  async purgeTrackerExcept(tracker: TrackerEnum, torrentIds: string[]) {
    const torrents = await this.webTorrentRunsService.find({
      where: {
        tracker,
        torrentId: Not(In(torrentIds)),
      },
    });

    await Promise.all(torrents.map((torrent) => this.delete(torrent.infoHash)));
  }

  updateUploadLimit(uploadLimit: number) {
    this.client.throttleUpload(uploadLimit);
  }

  async delete(infoHash: string): Promise<void> {
    const torrent = await this.getTorrent(infoHash);

    if (!torrent) {
      throw new NotFoundException(`A torrent nem fut: ${infoHash}`);
    }

    const downloadRoot = path.join(this.downloadsDir, torrent.name);

    await this.client.remove(torrent);

    try {
      await rm(downloadRoot, { recursive: true, force: true });
    } catch (error) {
      this.logger.error(
        `Nem sikerült törölni a könyvtárat: ${downloadRoot}`,
        error,
      );
    }

    await this.webTorrentRunsService.delete(infoHash);

    this.logger.log(
      `✅ Torrent és a könyvtára sikeresen törölve lett: ${torrent.name}`,
    );
  }

  async deleteAllByTracker(tracker: TrackerEnum): Promise<void> {
    const torrentRuns = await this.webTorrentRunsService.find();

    const trackerTorrentRuns = torrentRuns.filter(
      (torrentRun) => torrentRun.tracker === tracker,
    );

    await Promise.all(
      trackerTorrentRuns.map((trackerTorrentRun) =>
        this.delete(trackerTorrentRun.infoHash),
      ),
    );
  }
}
