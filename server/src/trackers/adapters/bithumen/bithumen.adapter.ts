import { Inject, Injectable } from '@nestjs/common';

import { MediaTypeEnum } from 'src/common/enum/media-type.enum';
import { LanguageEnum } from 'src/preference-items/enum/language.enum';
import { ResolutionEnum } from 'src/preference-items/enum/resolution.enum';
import { TrackerEnum } from 'src/trackers/enum/tracker.enum';
import {
  LoginRequest,
  TrackerAdapter,
  TrackerSearchQuery,
} from 'src/trackers/tracker.types';

import {
  AdapterParsedTorrent,
  AdapterTorrent,
  AdapterTorrentWithInfo,
  TRACKER_TOKEN,
} from '../adapters.types';
import { BithumenClient } from './bithumen.client';
import {
  MOVIE_CATEGORY_FILTERS,
  SERIES_CATEGORY_FILTERS,
} from './bithumen.constants';
import {
  BithumenMovieCategoryEnum,
  BithumenSeriesCategoryEnum,
} from './bithumen.types';

@Injectable()
export class BithumenAdapter implements TrackerAdapter {
  constructor(
    @Inject(TRACKER_TOKEN) readonly tracker: TrackerEnum,
    private client: BithumenClient,
  ) {}

  async login(payload: LoginRequest): Promise<void> {
    await this.client.login(payload);
  }

  async find(query: TrackerSearchQuery): Promise<AdapterTorrentWithInfo[]> {
    const { imdbId, mediaType } = query;

    let categories: string[] = [
      ...MOVIE_CATEGORY_FILTERS,
      ...SERIES_CATEGORY_FILTERS,
    ];

    switch (mediaType) {
      case MediaTypeEnum.MOVIE:
        categories = MOVIE_CATEGORY_FILTERS;
        break;

      case MediaTypeEnum.SERIES:
        categories = SERIES_CATEGORY_FILTERS;
        break;
    }

    const torrents = await this.client.find({ imdbId, categories });

    return torrents.map((torrent) => {
      const resolution = this.resolveTorrentResolution(torrent.category);
      const language = this.resolveVideoLanguage(torrent.category);

      return {
        tracker: this.tracker,
        imdbId: imdbId,
        torrentId: torrent.torrentId,
        seeders: Number(torrent.seeders),
        resolution,
        language,
        downloadUrl: torrent.downloadUrl,
      };
    });
  }

  async findOne(torrentId: string): Promise<AdapterTorrent> {
    return this.client.findOne(torrentId);
  }

  async download(payload: AdapterTorrent): Promise<AdapterParsedTorrent> {
    return this.client.download(payload);
  }

  async seedRequirement(): Promise<string[]> {
    return this.client.hitnrun();
  }

  private resolveTorrentResolution(
    category: BithumenMovieCategoryEnum | BithumenSeriesCategoryEnum,
  ): ResolutionEnum {
    switch (category) {
      case BithumenMovieCategoryEnum.SD:
      case BithumenMovieCategoryEnum.SD_HUN:
      case BithumenSeriesCategoryEnum.SD:
      case BithumenSeriesCategoryEnum.SD_HUN:
        return ResolutionEnum.R480P;

      case BithumenMovieCategoryEnum.HD:
      case BithumenMovieCategoryEnum.HD_HUN:
      case BithumenSeriesCategoryEnum.HD:
      case BithumenSeriesCategoryEnum.HD_HUN:
        return ResolutionEnum.R720P;

      case BithumenMovieCategoryEnum.FULL_HD:
      case BithumenMovieCategoryEnum.FULL_HD_HU:
      case BithumenMovieCategoryEnum.BLU_RAY:
      case BithumenMovieCategoryEnum.BLU_RAY_HU:
        return ResolutionEnum.R1080P;
    }
  }

  private resolveVideoLanguage(
    category: BithumenMovieCategoryEnum | BithumenSeriesCategoryEnum,
  ): LanguageEnum {
    const huCategories = [
      BithumenMovieCategoryEnum.SD_HUN,
      BithumenMovieCategoryEnum.HD_HUN,
      BithumenMovieCategoryEnum.FULL_HD_HU,
      BithumenMovieCategoryEnum.BLU_RAY_HU,
      BithumenSeriesCategoryEnum.SD_HUN,
      BithumenSeriesCategoryEnum.HD_HUN,
    ];

    if (huCategories.includes(category)) {
      return LanguageEnum.HU;
    } else {
      return LanguageEnum.EN;
    }
  }
}
