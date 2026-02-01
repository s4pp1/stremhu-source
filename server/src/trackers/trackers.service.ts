import {
  BadRequestException,
  Injectable,
  NotFoundException,
  NotImplementedException,
} from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { isUndefined, omitBy } from 'lodash';
import { EntityManager } from 'typeorm';

import { TorrentsCacheService } from 'src/torrents-cache/torrents-cache.service';
import { TorrentsService } from 'src/torrents/torrents.service';

import { DETAILS_PATH as BITHUMEN_DETAILS_PATH } from './adapters/bithumen/bithumen.constants';
import { DETAILS_PATH as INSANE_DETAILS_PATH } from './adapters/insane/insane.constants';
import { DETAILS_PATH as MAJOMPARADE_DETAILS_PATH } from './adapters/majomparade/majomparade.constants';
import { DETAILS_PATH as NCORE_DETAILS_PATH } from './adapters/ncore/ncore.constants';
import { TrackersStore } from './core/trackers.store';
import { TrackerEnum } from './enum/tracker.enum';
import { TrackerAdapterRegistry } from './tracker-adapter.registry';
import { LoginRequest } from './tracker.types';
import { TRACKER_INFO, TRACKER_OPTIONS } from './trackers.constants';
import { TrackerOptionWithUrl } from './type/tracker-option-with-url.type';
import { TrackerToUpdate } from './type/tracker-to-update.type';

@Injectable()
export class TrackersService {
  constructor(
    private readonly configService: ConfigService,
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
      if (error instanceof Error) {
        throw new BadRequestException(error.message);
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

  getTrackerOptionsWithUrl(): TrackerOptionWithUrl[] {
    const ncoreUrl = this.configService.getOrThrow<string>('tracker.ncore-url');
    const bithumenUrl = this.configService.getOrThrow<string>(
      'tracker.bithumen-url',
    );
    const insaneUrl =
      this.configService.getOrThrow<string>('tracker.insane-url');
    const majomparadeUrl = this.configService.getOrThrow<string>(
      'tracker.majomparade-url',
    );

    const trackerUrl = {
      [TrackerEnum.NCORE]: {
        url: ncoreUrl,
        detailsPath: NCORE_DETAILS_PATH,
      },
      [TrackerEnum.BITHUMEN]: {
        url: bithumenUrl,
        detailsPath: BITHUMEN_DETAILS_PATH,
      },
      [TrackerEnum.INSANE]: {
        url: insaneUrl,
        detailsPath: INSANE_DETAILS_PATH,
      },
      [TrackerEnum.MAJOMPARADE]: {
        url: majomparadeUrl,
        detailsPath: MAJOMPARADE_DETAILS_PATH,
      },
    };

    return TRACKER_OPTIONS.map((trackerOption) => ({
      ...trackerOption,
      url: trackerUrl[trackerOption.value].url,
      detailsPath: trackerUrl[trackerOption.value].detailsPath,
    }));
  }
}
