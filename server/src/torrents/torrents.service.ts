import {
  Inject,
  Injectable,
  Logger,
  NotFoundException,
  OnApplicationBootstrap,
  OnApplicationShutdown,
} from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { Cron, CronExpression } from '@nestjs/schedule';
import _ from 'lodash';
import { mkdir } from 'node:fs/promises';

import type {
  WebTorrentFile,
  WebTorrentTorrent,
} from 'src/clients/webtorrent/webtorrent.types';
import { safeReaddir } from 'src/common/utils/file.util';
import { TorrentCacheStore } from 'src/torrent-cache/core/torrent-cache.store';
import { TrackerEnum } from 'src/trackers/enum/tracker.enum';

import { TorrentsStore } from './core/torrents.store';
import { Torrent as TorrentEntity } from './entity/torrent.entity';
import type {
  TorrentClient,
  TorrentClientToUpdateConfig,
} from './ports/torrent-client.port';
import { TorrentToAddClient } from './type/torrent-to-add-client.type';
import { Torrent } from './type/torrent.type';

@Injectable()
export class TorrentsService
  implements OnApplicationBootstrap, OnApplicationShutdown
{
  private readonly logger = new Logger(TorrentsService.name);

  private readonly downloadsDir: string;

  constructor(
    private readonly configService: ConfigService,
    private readonly torrentsStore: TorrentsStore,
    @Inject('TorrentClient') private readonly torrentClient: TorrentClient,
    private readonly torrentCacheStore: TorrentCacheStore,
  ) {
    this.downloadsDir = this.configService.getOrThrow<string>(
      'web-torrent.downloads-dir',
    );
  }

  async onApplicationBootstrap() {
    // Downloads mappa létrehozása, ha nem létezik
    await mkdir(this.downloadsDir, { recursive: true });

    // Torrent kliens elindítása
    await this.torrentClient.bootstrap();
    this.logger.log('✅ WebTorrent kliens elindult');

    // Torrentek lekérése és visszarakása a kliensbe
    const torrents = await this.torrentsStore.find();

    for (const torrent of torrents) {
      const torrentCache = await this.torrentCacheStore.findOne({
        imdbId: torrent.imdbId,
        tracker: torrent.tracker,
        torrentId: torrent.torrentId,
      });

      if (!torrentCache) {
        this.logger.error(`❌ "${torrent.infoHash}" nem tölthető vissza.`);
        await this.torrentsStore.removeByInfoHash(torrent.infoHash);
        continue;
      }

      const clientTorrent = await this.torrentClient.addTorrent({
        parsedTorrent: torrentCache.parsed,
      });

      this.logger.log(`🔼 .torrent fájl betöltve: ${clientTorrent.name}`);
    }
  }

  async onApplicationShutdown(signal?: string) {
    this.logger.log(`🛑 Torrent kliens leállítása... signal: ${signal}`);

    // A futás óta feltöltött tartalom mennyiségének tárolása
    const clientTorrents = this.torrentClient.getTorrents();

    await Promise.all(
      clientTorrents.map((clientTorrent) =>
        this.torrentsStore.flushUploaded({
          infoHash: clientTorrent.infoHash,
          sessionBytes: clientTorrent.uploaded,
        }),
      ),
    );

    // Torrent kliens leállítása
    await this.torrentClient.shutdown();
  }

  async getTorrents(): Promise<Torrent[]> {
    const torrents = await this.torrentsStore.find();
    const clientTorrents = this.torrentClient.getTorrents();

    const activeTorrents: Torrent[] = [];

    for (const clientTorrent of clientTorrents) {
      const torrent = torrents.find(
        (torrent) => torrent.infoHash === clientTorrent.infoHash,
      );

      if (!torrent) {
        this.logger.warn(
          `⚠️ A ${clientTorrent.name} csak a kliensben létezik!`,
        );
        continue;
      }

      activeTorrents.push(
        this.mergeTorrentEntityWithTorrentClient(torrent, clientTorrent),
      );
    }

    return activeTorrents;
  }

  async getTorrent(infoHash: string): Promise<Torrent | null> {
    const [torrent, clientTorrent] = await Promise.all([
      this.torrentsStore.findOneByInfoHash(infoHash),
      this.torrentClient.getTorrent(infoHash),
    ]);

    if (!torrent || !clientTorrent) return null;

    return this.mergeTorrentEntityWithTorrentClient(torrent, clientTorrent);
  }

  async addTorrent(payload: TorrentToAddClient): Promise<Torrent> {
    const { parsedTorrent, ...rest } = payload;

    const clientTorrent = await this.torrentClient.addTorrent({
      parsedTorrent,
    });

    const torrent = await this.torrentsStore.create({
      ...rest,
      infoHash: clientTorrent.infoHash,
    });

    return this.mergeTorrentEntityWithTorrentClient(torrent, clientTorrent);
  }

  async getTorrentFile(
    infoHash: string,
    fileIndex: number,
  ): Promise<WebTorrentFile> {
    const clientTorrent = await this.torrentClient.getTorrent(infoHash);

    if (!clientTorrent.files[fileIndex]) {
      throw new NotFoundException(
        `A(z) "${clientTorrent.name}-ben nincs ilyen fileIndex: ${fileIndex}. Fájlok száma: ${clientTorrent.files.length}`,
      );
    }
    return clientTorrent.files[fileIndex];
  }

  async purgeTrackerExcept(tracker: TrackerEnum, torrentIds: string[]) {
    const torrents = await this.torrentsStore.find((qb) => {
      qb.where('torrent.tracker = :tracker', { tracker });

      if (torrentIds.length) {
        qb.andWhere('torrent.torrentId NOT IN (:...torrentIds)', {
          torrentIds,
        });
      }

      return qb;
    });

    await Promise.all(torrents.map((torrent) => this.delete(torrent.infoHash)));
  }

  updateTorrentClient(payload: TorrentClientToUpdateConfig) {
    this.torrentClient.updateConfig(payload);
  }

  async delete(infoHash: string): Promise<void> {
    try {
      await this.torrentClient.deleteTorrent(infoHash);
      await this.torrentsStore.removeByInfoHash(infoHash);
    } catch (error) {
      this.logger.error(
        `🚨 "${infoHash}" torrent törlése közben hiba történt!`,
        error,
      );
    }
  }

  async deleteAllByTracker(tracker: TrackerEnum): Promise<void> {
    const torrents = await this.torrentsStore.find();

    const trackerTorrents = torrents.filter(
      (torrentRun) => torrentRun.tracker === tracker,
    );

    await Promise.all(
      trackerTorrents.map((trackerTorrent) =>
        this.delete(trackerTorrent.infoHash),
      ),
    );
  }

  private mergeTorrentEntityWithTorrentClient(
    torrentEntity: TorrentEntity,
    webTorrentTorrent: WebTorrentTorrent,
  ): Torrent {
    return {
      name: webTorrentTorrent.name,
      imdbId: torrentEntity.imdbId,
      tracker: torrentEntity.tracker,
      torrentId: torrentEntity.torrentId,
      infoHash: torrentEntity.infoHash,
      downloaded: webTorrentTorrent.downloaded,
      progress: webTorrentTorrent.progress,
      total: webTorrentTorrent.length,
      uploaded: webTorrentTorrent.uploaded + torrentEntity.uploaded,
      uploadSpeed: webTorrentTorrent.uploadSpeed,
      updatedAt: torrentEntity.updatedAt,
      createdAt: torrentEntity.createdAt,
    };
  }

  @Cron(CronExpression.EVERY_10_SECONDS)
  async cleanupOrphanTorrents() {
    const nowMs = new Date().getTime();

    const [torrents, torrentDirents] = await Promise.all([
      this.getTorrents(),
      safeReaddir(this.downloadsDir),
    ]);

    const torrentNames = torrentDirents.map(
      (torrentDirent) => torrentDirent.name,
    );

    const orphanTorrents = _.differenceWith(
      torrents,
      torrentNames,
      (torrent, torrentName) => torrent.name === torrentName,
    );

    const deletePromise: Promise<void>[] = [];

    orphanTorrents.forEach((orphanTorrent) => {
      const ageMs = nowMs - new Date(orphanTorrent.createdAt).getTime();
      if (ageMs < 10_000) return;

      deletePromise.push(
        this.torrentsStore.removeByInfoHash(orphanTorrent.infoHash),
      );
    });

    try {
      await Promise.all(deletePromise);
    } catch (error) {
      this.logger.error(error);
    }
  }
}
