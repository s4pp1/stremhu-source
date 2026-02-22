import { Injectable, Logger, NotFoundException } from '@nestjs/common';

import { RelayTorrent, UpdateSettings } from 'src/relay/client';
import { RelayService } from 'src/relay/relay.service';
import { TrackersStore } from 'src/trackers/core/trackers.store';
import { TrackerEnum } from 'src/trackers/enum/tracker.enum';

import { PersistedTorrentsStore } from './persisted/core/persisted-torrents.store';
import { PersistedTorrent } from './persisted/entity/torrent.entity';
import { PersistedTorrentsService } from './persisted/persisted-torrents.service';
import { TorrentToAdd } from './type/torrent-to-add.type';
import { TorrentToUpdate } from './type/torrent-to-update.type';
import { Torrent } from './type/torrent.type';

@Injectable()
export class TorrentsService {
  private readonly logger = new Logger(TorrentsService.name);

  constructor(
    private readonly persistedTorrentsStore: PersistedTorrentsStore,
    private readonly persistedTorrentsService: PersistedTorrentsService,
    private readonly relayService: RelayService,
    private readonly trackersStore: TrackersStore,
  ) {}

  async find(): Promise<Torrent[]> {
    const [persistedTorrents, relayTorrents] = await Promise.all([
      this.persistedTorrentsService.find(),
      this.relayService.getTorrents(),
    ]);

    const persistedTorrentMap = new Map(
      persistedTorrents.map((persistedTorrent) => [
        persistedTorrent.infoHash,
        persistedTorrent,
      ]),
    );

    const activeTorrents: Torrent[] = [];

    for (const relayTorrent of relayTorrents) {
      const persistedTorrent = persistedTorrentMap.get(relayTorrent.infoHash);

      if (!persistedTorrent) {
        this.logger.warn(`⚠️ A ${relayTorrent.name} csak a kliensben létezik!`);
        continue;
      }

      activeTorrents.push(
        this.mergePersistAndRelay(persistedTorrent, relayTorrent),
      );
    }

    return activeTorrents;
  }

  async findOneByInfoHash(infoHash: string): Promise<Torrent | null> {
    const [persistedTorrent, relayTorrent] = await Promise.all([
      this.persistedTorrentsService.findOneByInfoHash(infoHash),
      this.relayService.getTorrent(infoHash),
    ]);

    if (!persistedTorrent || !relayTorrent) return null;

    return this.mergePersistAndRelay(persistedTorrent, relayTorrent);
  }

  async findOneByInfoHashOrThrow(infoHash: string): Promise<Torrent> {
    const torrent = await this.findOneByInfoHash(infoHash);

    if (!torrent) {
      throw new NotFoundException(`A(z) "${infoHash}" torrent nem található`);
    }

    return torrent;
  }

  async addTorrent(payload: TorrentToAdd): Promise<Torrent> {
    const { tracker: trackerEnum, torrentFilePath, ...rest } = payload;

    const tracker = await this.trackersStore.findOneByTracker(trackerEnum);

    const relayTorrent = await this.relayService.addTorrent({
      torrentFilePath,
      downloadFullTorrent: tracker?.downloadFullTorrent ?? false,
    });

    const persistedTorrent = await this.persistedTorrentsService.create({
      ...rest,

      tracker: trackerEnum,
      infoHash: relayTorrent.infoHash,
    });

    return this.mergePersistAndRelay(persistedTorrent, relayTorrent);
  }

  async updateOne(
    infoHash: string,
    payload: TorrentToUpdate,
  ): Promise<Torrent> {
    const updatedPersistedTorrent =
      await this.persistedTorrentsService.updateOne(infoHash, payload);

    if (payload.fullDownload !== undefined) {
      let fullDownload = payload.fullDownload;

      if (fullDownload === null) {
        const tracker = await this.trackersStore.findOneByTracker(
          updatedPersistedTorrent.tracker,
        );

        fullDownload = tracker?.downloadFullTorrent ?? false;
      }

      await this.relayService.updateTorrent(infoHash, {
        downloadFullTorrent: fullDownload,
      });
    }

    return this.findOneByInfoHashOrThrow(infoHash);
  }

  async cleanupTrackerTorrents(
    tracker: TrackerEnum,
    keepSeedSeconds: number | undefined,
    notCompletedTorrentIds?: string[],
  ) {
    const persistedTorrents = await this.persistedTorrentsStore.find((qb) => {
      qb.where(
        'torrent.tracker = :tracker AND torrent.isPersisted = :isPersisted',
        {
          tracker,
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

    await Promise.all(
      persistedTorrents.map((persistedTorrent) =>
        this.delete(persistedTorrent.infoHash),
      ),
    );
  }

  async updateTorrentClient(payload: UpdateSettings) {
    await this.relayService.updateConfig(payload);
  }

  async deleteAllByTracker(tracker: TrackerEnum): Promise<void> {
    const persistedTorrents = await this.persistedTorrentsStore.find((qb) => {
      qb.where(
        'torrent.tracker = :tracker AND torrent.isPersisted = :isPersisted',
        {
          tracker,
          isPersisted: false,
        },
      );

      return qb;
    });

    await Promise.all(
      persistedTorrents.map((persistedTorrent) =>
        this.delete(persistedTorrent.infoHash),
      ),
    );
  }

  async delete(infoHash: string): Promise<void> {
    try {
      const torrent = await this.findOneByInfoHashOrThrow(infoHash);

      await Promise.all([
        this.relayService.deleteTorrent(torrent.infoHash),
        this.persistedTorrentsService.deleteByInfoHash(torrent.infoHash),
      ]);
    } catch (error) {
      this.logger.error(
        `🚨 "${infoHash}" torrent törlése közben hiba történt!`,
        error,
      );

      throw error;
    }
  }

  private mergePersistAndRelay(
    persistedTorrent: PersistedTorrent,
    relayTorrent: RelayTorrent,
  ): Torrent {
    return {
      name: relayTorrent.name,
      tracker: persistedTorrent.tracker,
      torrentId: persistedTorrent.torrentId,
      infoHash: persistedTorrent.infoHash,
      isPersisted: persistedTorrent.isPersisted,
      fullDownload: persistedTorrent.fullDownload,
      downloaded: relayTorrent.downloaded,
      progress: relayTorrent.progress,
      total: relayTorrent.total,
      connections: relayTorrent.connections,
      maxConnections: relayTorrent.maxConnections,
      uploaded: relayTorrent.uploaded + persistedTorrent.uploaded,
      downloadSpeed: relayTorrent.downloadSpeed,
      uploadSpeed: relayTorrent.uploadSpeed,
      lastPlayedAt: persistedTorrent.lastPlayedAt,
      updatedAt: persistedTorrent.updatedAt,
      createdAt: persistedTorrent.createdAt,
    };
  }
}
