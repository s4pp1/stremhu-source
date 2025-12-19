import {
  BadRequestException,
  HttpException,
  Injectable,
  NotImplementedException,
} from '@nestjs/common';
import { EntityManager } from 'typeorm';

import { TorrentCacheService } from 'src/torrent-cache/torrent-cache.service';
import { TorrentsService } from 'src/torrents/torrents.service';

import { TrackersStore } from './core/trackers.store';
import { TrackerEnum } from './enum/tracker.enum';
import { TrackerAdapterRegistry } from './tracker-adapter.registry';
import { LoginRequest } from './tracker.types';
import { LOGIN_ERROR_MESSAGE, TRACKER_INFO } from './trackers.constants';

@Injectable()
export class TrackersService {
  constructor(
    private readonly trackerAdapterRegistry: TrackerAdapterRegistry,
    private readonly trackersStore: TrackersStore,
    private readonly torrentsService: TorrentsService,
    private readonly torrentCacheService: TorrentCacheService,
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

  async delete(tracker: TrackerEnum, manager?: EntityManager): Promise<void> {
    const foundTracker = await this.trackersStore.findOneByTracker(tracker);

    if (!foundTracker) {
      throw new BadRequestException(`A(z) "${tracker}" nem található.`);
    }

    await this.torrentsService.deleteAllByTracker(tracker);
    await this.torrentCacheService.deleteAllByTracker(tracker);
    await this.trackersStore.remove(foundTracker, manager);
  }
}
