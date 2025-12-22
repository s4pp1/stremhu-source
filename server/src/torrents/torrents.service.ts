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
import _, { isUndefined, omitBy } from 'lodash';
import { mkdir } from 'node:fs/promises';

import type {
  WebTorrentFile,
  WebTorrentTorrent,
} from 'src/clients/webtorrent/webtorrent.types';
import { safeReaddir } from 'src/common/utils/file.util';
import { TorrentsCacheStore } from 'src/torrents-cache/core/torrents-cache.store';
import { TrackersStore } from 'src/trackers/core/trackers.store';
import { TrackerEnum } from 'src/trackers/enum/tracker.enum';

import { TorrentsStore } from './core/torrents.store';
import { Torrent, Torrent as TorrentEntity } from './entity/torrent.entity';
import type {
  TorrentClient,
  TorrentClientToUpdateConfig,
} from './ports/torrent-client.port';
import { TorrentToAddClient } from './type/torrent-to-add-client.type';
import { TorrentToUpdate } from './type/torrent-to-update.type';
import { MergedTorrent } from './type/torrent.type';

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
    private readonly trackersStore: TrackersStore,
    private readonly torrentsCacheStore: TorrentsCacheStore,
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

    // Torrentek lekérése és visszarakása a kliensbe
    const torrents = await this.torrentsStore.find();

    // Tracker-ek letöltése
    const trackers = await this.trackersStore.find();

    for (const torrent of torrents) {
      const torrentCache = await this.torrentsCacheStore.findOne({
        imdbId: torrent.imdbId,
        tracker: torrent.tracker,
        torrentId: torrent.torrentId,
      });

      if (!torrentCache) {
        this.logger.error(`🚨 "${torrent.infoHash}" nem tölthető vissza.`);
        await this.torrentsStore.removeByInfoHash(torrent.infoHash);
        continue;
      }

      const tracker = trackers.find(
        (tracker) => tracker.tracker === torrent.tracker,
      );

      this.torrentClient
        .addTorrent({
          parsedTorrent: torrentCache.parsed,
          downloadFullTorrent: tracker?.downloadFullTorrent ?? false,
        })
        .then((clientTorrent) => {
          this.logger.log(`🔼 .torrent fájl betöltve: ${clientTorrent.name}`);
        })
        .catch(() => {
          this.logger.error(
            `🚨 .torrent fájl betöltése közben hiba történt: ${torrentCache.parsed.name}`,
          );
        });
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

  async getTorrentOrThrow(infoHash: string): Promise<Torrent> {
    const torrent = await this.torrentsStore.findOneByInfoHash(infoHash);

    if (!torrent) {
      throw new NotFoundException(`A(z) "${infoHash}" torrent nem található.`);
    }

    return torrent;
  }

  async getTorrents(): Promise<MergedTorrent[]> {
    const torrents = await this.torrentsStore.find();
    const clientTorrents = this.torrentClient.getTorrents();

    const activeTorrents: MergedTorrent[] = [];

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

  async getTorrent(infoHash: string): Promise<MergedTorrent | null> {
    const [torrent, clientTorrent] = await Promise.all([
      this.torrentsStore.findOneByInfoHash(infoHash),
      this.torrentClient.getTorrent(infoHash),
    ]);

    if (!torrent || !clientTorrent) return null;

    return this.mergeTorrentEntityWithTorrentClient(torrent, clientTorrent);
  }

  async updateOneOrThrow(
    infoHash: string,
    payload: TorrentToUpdate,
  ): Promise<Torrent> {
    const torrent = await this.getTorrentOrThrow(infoHash);

    const updateData = omitBy(payload, isUndefined);

    const updatedTorrent = this.torrentsStore.updateOne({
      ...torrent,
      ...updateData,
    });

    return updatedTorrent;
  }

  async updateOneForRest(infoHash: string, payload: TorrentToUpdate) {
    const torrent = await this.updateOneOrThrow(infoHash, payload);
    const clientTorrent = await this.getTorrentForStreamOrThrow(
      torrent.infoHash,
    );

    return this.mergeTorrentEntityWithTorrentClient(torrent, clientTorrent);
  }

  async cleanupTrackerTorrents(
    trackerEnum: TrackerEnum,
    keepSeedSeconds: number | undefined,
    notCompletedTorrentIds?: string[],
  ) {
    const torrents = await this.torrentsStore.find((qb) => {
      qb.where(
        'torrent.tracker = :tracker AND torrent.isPersisted = :isPersisted',
        {
          tracker: trackerEnum,
          isPersisted: false,
        },
      );

      if (notCompletedTorrentIds?.length) {
        qb.andWhere('torrent.torrentId NOT IN (:...notCompletedTorrentIds)', {
          notCompletedTorrentIds,
        });
      }

      if (keepSeedSeconds) {
        qb.andWhere(
          "datetime(torrent.lastPlayedAt, '+' || :keepSeedSeconds || ' seconds') < datetime('now')",
          { keepSeedSeconds },
        );
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
      const webTorrentTorrent = await this.torrentClient.getTorrent(infoHash);

      if (!webTorrentTorrent) {
        throw new NotFoundException(`A(z) "${infoHash}" torrent nem található`);
      }

      await this.torrentClient.deleteTorrent(webTorrentTorrent);
      await this.torrentsStore.removeByInfoHash(webTorrentTorrent.infoHash);
    } catch (error) {
      this.logger.error(
        `🚨 "${infoHash}" torrent törlése közben hiba történt!`,
        error,
      );

      throw error;
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

  async getTorrentForStream(
    infoHash: string,
  ): Promise<WebTorrentTorrent | null> {
    const webTorrentTorrent = await this.torrentClient.getTorrent(infoHash);

    if (!webTorrentTorrent) {
      return null;
    }

    await this.updateOneOrThrow(infoHash, { lastPlayedAt: new Date() });

    return webTorrentTorrent;
  }

  async getTorrentForStreamOrThrow(
    infoHash: string,
  ): Promise<WebTorrentTorrent> {
    const clientTorrent = await this.getTorrentForStream(infoHash);

    if (!clientTorrent) {
      throw new NotFoundException(`A(z) "${infoHash}" torrent nem található.`);
    }

    return clientTorrent;
  }

  async addTorrentForStream(
    payload: TorrentToAddClient,
  ): Promise<WebTorrentTorrent> {
    const { tracker: trackerEnum, parsedTorrent, ...rest } = payload;

    const tracker = await this.trackersStore.findOneByTracker(trackerEnum);

    const clientTorrent = await this.torrentClient.addTorrent({
      parsedTorrent,
      downloadFullTorrent: tracker?.downloadFullTorrent ?? false,
    });

    await this.torrentsStore.create({
      ...rest,
      tracker: trackerEnum,
      infoHash: clientTorrent.infoHash,
      lastPlayedAt: new Date(),
    });

    return clientTorrent;
  }

  getTorrentFileForStream(
    webTorrentTorrent: WebTorrentTorrent,
    fileIndex: number,
  ): WebTorrentFile {
    if (!webTorrentTorrent.files[fileIndex]) {
      throw new NotFoundException(
        `A(z) "${webTorrentTorrent.name}-ben nincs ilyen fileIndex: ${fileIndex}. Fájlok száma: ${webTorrentTorrent.files.length}`,
      );
    }
    return webTorrentTorrent.files[fileIndex];
  }

  private mergeTorrentEntityWithTorrentClient(
    torrentEntity: TorrentEntity,
    webTorrentTorrent: WebTorrentTorrent,
  ): MergedTorrent {
    return {
      name: webTorrentTorrent.name,
      imdbId: torrentEntity.imdbId,
      tracker: torrentEntity.tracker,
      torrentId: torrentEntity.torrentId,
      infoHash: torrentEntity.infoHash,
      isPersisted: torrentEntity.isPersisted,
      downloaded: webTorrentTorrent.downloaded,
      progress: webTorrentTorrent.progress,
      total: webTorrentTorrent.length,
      uploaded: webTorrentTorrent.uploaded + torrentEntity.uploaded,
      downloadSpeed: webTorrentTorrent.downloadSpeed,
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
