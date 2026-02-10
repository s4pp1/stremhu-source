import {
  BadRequestException,
  Injectable,
  Logger,
  NotFoundException,
} from '@nestjs/common';
import { isUndefined, omitBy } from 'lodash';

import { TrackerEnum } from 'src/trackers/enum/tracker.enum';
import { TRACKER_INFO } from 'src/trackers/trackers.constants';

import { PersistedTorrentsStore } from './core/persisted-torrents.store';
import { PersistedTorrent } from './entity/torrent.entity';
import { PersistedTorrentToCreate } from './type/persisted-torrent-to-create.type';
import { PersistedTorrentToUpdate } from './type/persisted-torrent-to-update.type';

@Injectable()
export class PersistedTorrentsService {
  private readonly logger = new Logger(PersistedTorrentsService.name);

  constructor(
    private readonly persistedTorrentsStore: PersistedTorrentsStore,
  ) {}

  async find(): Promise<PersistedTorrent[]> {
    const persistedTorrents = await this.persistedTorrentsStore.find();
    return persistedTorrents;
  }

  async findOneByInfoHash(infoHash: string): Promise<PersistedTorrent | null> {
    const persistedTorrent = await this.persistedTorrentsStore.findOne((qb) => {
      qb.where('torrent.infoHash = :infoHash', { infoHash });
      return qb;
    });

    return persistedTorrent;
  }

  async findOneByInfoHashOrThrow(infoHash: string): Promise<PersistedTorrent> {
    const persistedTorrent = await this.findOneByInfoHash(infoHash);

    if (!persistedTorrent) {
      throw new NotFoundException(`A(z) "${infoHash}" torrent nem található.`);
    }

    return persistedTorrent;
  }

  async create(payload: PersistedTorrentToCreate) {
    const entity = this.persistedTorrentsStore.createEntity({
      ...payload,
      lastPlayedAt: new Date(),
    });
    return this.persistedTorrentsStore.createOrUpdate(entity);
  }

  async updateOne(
    infoHash: string,
    payload: PersistedTorrentToUpdate,
    existingEntity?: PersistedTorrent,
  ): Promise<PersistedTorrent> {
    let persistedTorrent = existingEntity;

    if (!persistedTorrent) {
      persistedTorrent = await this.findOneByInfoHashOrThrow(infoHash);
    }

    const tracker = TRACKER_INFO[persistedTorrent.tracker];

    if (payload.fullDownload !== undefined && tracker.requiresFullDownload) {
      throw new BadRequestException(
        `A(z) "${tracker.label}" torrent esetén nem írható felül a globális beállítás.`,
      );
    }

    const updateData = omitBy(payload, isUndefined);

    const updatedTorrent = this.persistedTorrentsStore.createOrUpdate({
      ...persistedTorrent,
      ...updateData,
    });

    return updatedTorrent;
  }

  async deleteByInfoHash(infoHash: string): Promise<void> {
    try {
      const persistedTorrent = await this.findOneByInfoHashOrThrow(infoHash);
      await this.persistedTorrentsStore.delete(persistedTorrent);
    } catch (error) {
      this.logger.error(
        `🚨 "${infoHash}" torrent törlése közben hiba történt!`,
        error,
      );

      throw error;
    }
  }

  async deleteByTracker(tracker: TrackerEnum): Promise<void> {
    const persistedTorrents = await this.persistedTorrentsStore.find((qb) => {
      qb.where('torrent.tracker = :tracker', { tracker });
      return qb;
    });

    await Promise.all(
      persistedTorrents.map((trackerTorrent) =>
        this.deleteByInfoHash(trackerTorrent.infoHash),
      ),
    );
  }
}
