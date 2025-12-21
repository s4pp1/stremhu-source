import { Resolution as ResolutionEnum } from '@ctrl/video-filename-parser';
import { Inject, Injectable } from '@nestjs/common';

import { LanguageEnum } from 'src/common/enum/language.enum';
import { StreamMediaTypeEnum } from 'src/stremio/enum/stream-media-type.enum';
import { TrackerEnum } from 'src/trackers/enum/tracker.enum';
import {
  LoginRequest,
  TrackerAdapter,
  TrackerSearchQuery,
} from 'src/trackers/tracker.types';

import {
  AdapterParsedTorrent,
  AdapterTorrent,
  AdapterTorrentId,
  TRACKER_TOKEN,
} from '../adapters.types';
import { BithumenClient } from './bithumen.client';
import {
  BITHUMEN_MOVIE_CATEGORY_FILTERS,
  BITHUMEN_SERIES_CATEGORY_FILTERS,
} from './bithumen.constants';
import {
  BithumenMovieCategoryEnum,
  BithumenSeriesCategoryEnum,
} from './bithumen.types';

@Injectable()
export class BithumenAdapter implements TrackerAdapter {
  constructor(
    @Inject(TRACKER_TOKEN) readonly tracker: TrackerEnum,
    private bithumenClient: BithumenClient,
  ) {}

  async login(payload: LoginRequest): Promise<void> {
    await this.bithumenClient.login(payload);
  }

  async find(query: TrackerSearchQuery): Promise<AdapterTorrent[]> {
    const { imdbId, mediaType } = query;

    let categories: string[] = [
      ...BITHUMEN_MOVIE_CATEGORY_FILTERS,
      ...BITHUMEN_SERIES_CATEGORY_FILTERS,
    ];

    switch (mediaType) {
      case StreamMediaTypeEnum.MOVIE:
        categories = BITHUMEN_MOVIE_CATEGORY_FILTERS;
        break;

      case StreamMediaTypeEnum.SERIES:
        categories = BITHUMEN_SERIES_CATEGORY_FILTERS;
        break;
    }

    const torrents = await this.bithumenClient.find({ imdbId, categories });

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

  async findOne(torrentId: string): Promise<AdapterTorrentId> {
    return this.bithumenClient.findOne(torrentId);
  }

  async download(payload: AdapterTorrentId): Promise<AdapterParsedTorrent> {
    return this.bithumenClient.download(payload);
  }

  async seedRequirement(): Promise<string[]> {
    return this.bithumenClient.hitnrun();
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
