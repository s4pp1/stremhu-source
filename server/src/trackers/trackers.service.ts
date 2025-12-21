import {
  BadRequestException,
  HttpException,
  Injectable,
  NotFoundException,
  NotImplementedException,
} from '@nestjs/common';
import { isUndefined, omitBy } from 'lodash';
import { EntityManager } from 'typeorm';

import { TorrentsCacheService } from 'src/torrents-cache/torrents-cache.service';
import { TorrentsService } from 'src/torrents/torrents.service';

import { TrackersStore } from './core/trackers.store';
import { TrackerEnum } from './enum/tracker.enum';
import { TrackerAdapterRegistry } from './tracker-adapter.registry';
import { LoginRequest } from './tracker.types';
import { LOGIN_ERROR_MESSAGE, TRACKER_INFO } from './trackers.constants';
import { TrackerToUpdate } from './type/tracker-to-update';

@Injectable()
export class TrackersService {
  constructor(
    private readonly trackerAdapterRegistry: TrackerAdapterRegistry,
    private readonly trackersStore: TrackersStore,
    private readonly torrentsService: TorrentsService,
    private readonly torrentsCacheService: TorrentsCacheService,
  ) {}

  async login(tracker: TrackerEnum, payload: LoginRequest): Promise<void> {
    try {
      const foundTracker = await this.trackersStore.findOneByTracker(tracker);

      if (foundTracker) {
        throw new BadRequestException(`A(z) "${tracker}" már hozzá van adva.`);
      }

      const adapter = this.trackerAdapterRegistry.get(tracker);
      await adapter.login(payload);

      const trackers = await this.trackersStore.find();

      await this.trackersStore.create({
        tracker,
        ...payload,
        keepSeedSeconds: null,
        hitAndRun: null,
        orderIndex: trackers.length,
        downloadFullTorrent: TRACKER_INFO[tracker].requiresFullDownload,
      });
    } catch (error) {
      if (error instanceof HttpException) {
        if (error.getStatus() === 422) {
          throw new BadRequestException(LOGIN_ERROR_MESSAGE);
        }

        throw error;
      }

      throw new NotImplementedException(
        `Bejelentkezés közben hiba történt, próbáld újra!`,
      );
    }
  }

  async findOneOrThrow(tracker: TrackerEnum) {
    const item = await this.trackersStore.findOneByTracker(tracker);

    if (!item) {
      throw new NotFoundException(`A(z) "${tracker}" nem található.`);
    }

    return item;
  }

  async updateOneOrThrow(tracker: TrackerEnum, payload: TrackerToUpdate) {
    const { downloadFullTorrent } = payload;

    if (downloadFullTorrent !== undefined) {
      const rule = TRACKER_INFO[tracker].requiresFullDownload;

      if (rule && !downloadFullTorrent) {
        throw new BadRequestException(
          `A(z) "${TRACKER_INFO[tracker].label}" esetén a teljes letöltés nem kapcsolható ki.`,
        );
      }
    }

    const item = await this.findOneOrThrow(tracker);

    const updateData = omitBy(payload, isUndefined);

    const updatedTorrent = this.trackersStore.updateOne({
      ...item,
      ...updateData,
    });

    return updatedTorrent;
  }

  async delete(tracker: TrackerEnum, manager?: EntityManager): Promise<void> {
    const foundTracker = await this.trackersStore.findOneByTracker(tracker);

    if (!foundTracker) {
      throw new BadRequestException(`A(z) "${tracker}" nem található.`);
    }

    await this.torrentsService.deleteAllByTracker(tracker);
    await this.torrentsCacheService.deleteAllByTracker(tracker);
    await this.trackersStore.remove(foundTracker, manager);
  }
}
