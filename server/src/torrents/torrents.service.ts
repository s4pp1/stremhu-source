import {
  BadRequestException,
  Injectable,
  Logger,
  NotFoundException,
  OnApplicationBootstrap,
  OnApplicationShutdown,
} from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
// import { Cron, CronExpression } from '@nestjs/schedule';
import _, { isUndefined, omitBy } from 'lodash';
import { mkdir } from 'node:fs/promises';

import { safeReaddir } from 'src/common/utils/file.util';
import { RelayTorrent, UpdateSettings } from 'src/relay/client';
import { RelayService } from 'src/relay/relay.service';
import { TorrentsCacheStore } from 'src/torrents-cache/core/torrents-cache.store';
import { TrackersStore } from 'src/trackers/core/trackers.store';
import { TrackerEnum } from 'src/trackers/enum/tracker.enum';
import { TRACKER_INFO } from 'src/trackers/trackers.constants';

import { TorrentsStore } from './core/torrents.store';
import { Torrent, Torrent as TorrentEntity } from './entity/torrent.entity';
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
    private readonly relayService: RelayService,
    private readonly trackersStore: TrackersStore,
    private readonly torrentsCacheStore: TorrentsCacheStore,
  ) {
    this.downloadsDir = this.configService.getOrThrow<string>(
      'torrent.downloads-dir',
    );
  }

  async onApplicationBootstrap() {
    // Downloads mappa létrehozása, ha nem létezik
    await mkdir(this.downloadsDir, { recursive: true });

    // Torrent kliens elindítása
    await this.relayService.bootstrap();

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

      let downloadFullTorrent = tracker?.downloadFullTorrent ?? false;

      if (torrent.fullDownload !== null) {
        downloadFullTorrent = torrent.fullDownload;
      }

      this.relayService
        .addTorrent({
          torrentFilePath: torrentCache.torrentFilePath,
          downloadFullTorrent: downloadFullTorrent,
        })
        .then((relayTorrent) => {
          this.logger.log(`🔼 .torrent fájl betöltve: ${relayTorrent.name}`);
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
    const clientTorrents = await this.relayService.getTorrents();

    await Promise.all(
      clientTorrents.map((clientTorrent) =>
        this.torrentsStore.flushUploaded({
          infoHash: clientTorrent.infoHash,
          sessionBytes: clientTorrent.uploaded,
        }),
      ),
    );

    // Torrent kliens leállítása
    await this.relayService.shutdown();
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
    const relayTorrents = await this.relayService.getTorrents();

    const activeTorrents: MergedTorrent[] = [];

    for (const relayTorrent of relayTorrents) {
      const torrent = torrents.find(
        (torrent) => torrent.infoHash === relayTorrent.infoHash,
      );

      if (!torrent) {
        this.logger.warn(`⚠️ A ${relayTorrent.name} csak a kliensben létezik!`);
        continue;
      }

      activeTorrents.push(
        this.mergeTorrentEntityWithTorrentClient(torrent, relayTorrent),
      );
    }

    return activeTorrents;
  }

  async getTorrent(infoHash: string): Promise<MergedTorrent | null> {
    const [torrent, clientTorrent] = await Promise.all([
      this.torrentsStore.findOneByInfoHash(infoHash),
      this.relayService.getTorrent(infoHash),
    ]);

    if (!torrent || !clientTorrent) return null;

    return this.mergeTorrentEntityWithTorrentClient(torrent, clientTorrent);
  }

  async updateOneOrThrow(
    infoHash: string,
    payload: TorrentToUpdate,
  ): Promise<Torrent> {
    const torrent = await this.getTorrentOrThrow(infoHash);

    const tracker = TRACKER_INFO[torrent.tracker];

    if (payload.fullDownload !== undefined) {
      if (tracker.requiresFullDownload) {
        throw new BadRequestException(
          `A(z) "${tracker.label}" torrent esetén nem írható felül a globális beállítás.`,
        );
      }

      let fullDownload = payload.fullDownload;

      if (fullDownload === null) {
        const tracker = await this.trackersStore.findOneByTracker(
          torrent.tracker,
        );

        fullDownload = tracker?.downloadFullTorrent ?? false;
      }

      await this.relayService.updateTorrent(infoHash, {
        downloadFullTorrent: fullDownload,
      });
    }

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

  async updateTorrentClient(payload: UpdateSettings) {
    await this.relayService.updateConfig(payload);
  }

  async delete(infoHash: string): Promise<void> {
    try {
      const webTorrentTorrent = await this.relayService.getTorrent(infoHash);

      if (!webTorrentTorrent) {
        throw new NotFoundException(`A(z) "${infoHash}" torrent nem található`);
      }

      await this.relayService.deleteTorrent(webTorrentTorrent.infoHash);
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

  async getTorrentForStream(infoHash: string): Promise<RelayTorrent | null> {
    const clientTorrent = await this.relayService.getTorrent(infoHash);

    if (!clientTorrent) {
      return null;
    }

    await this.updateOneOrThrow(infoHash, { lastPlayedAt: new Date() });

    return clientTorrent;
  }

  async getTorrentForStreamOrThrow(infoHash: string): Promise<RelayTorrent> {
    const clientTorrent = await this.getTorrentForStream(infoHash);

    if (!clientTorrent) {
      throw new NotFoundException(`A(z) "${infoHash}" torrent nem található.`);
    }

    return clientTorrent;
  }

  async addTorrentForStream(
    payload: TorrentToAddClient,
  ): Promise<RelayTorrent> {
    const { tracker: trackerEnum, torrentFilePath, ...rest } = payload;

    const tracker = await this.trackersStore.findOneByTracker(trackerEnum);

    const clientTorrent = await this.relayService.addTorrent({
      torrentFilePath,
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

  private mergeTorrentEntityWithTorrentClient(
    torrentEntity: TorrentEntity,
    relayTorrent: RelayTorrent,
  ): MergedTorrent {
    return {
      name: relayTorrent.name,
      imdbId: torrentEntity.imdbId,
      tracker: torrentEntity.tracker,
      torrentId: torrentEntity.torrentId,
      infoHash: torrentEntity.infoHash,
      isPersisted: torrentEntity.isPersisted,
      fullDownload: torrentEntity.fullDownload,
      downloaded: relayTorrent.downloaded,
      progress: relayTorrent.progress,
      total: relayTorrent.total,
      uploaded: relayTorrent.uploaded + torrentEntity.uploaded,
      downloadSpeed: relayTorrent.downloadSpeed,
      uploadSpeed: relayTorrent.uploadSpeed,
      updatedAt: torrentEntity.updatedAt,
      createdAt: torrentEntity.createdAt,
    };
  }

  // @Cron(CronExpression.EVERY_10_SECONDS)
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
