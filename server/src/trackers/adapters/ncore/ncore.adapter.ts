import { Inject, Injectable } from '@nestjs/common';

import { MediaTypeEnum } from 'src/common/enum/media-type.enum';
import { LanguageEnum } from 'src/preference-items/enum/language.enum';
import { ResolutionEnum } from 'src/preference-items/enum/resolution.enum';

import { TrackerEnum } from '../../enum/tracker.enum';
import {
  LoginRequest,
  TrackerAdapter,
  TrackerSearchQuery,
} from '../../tracker.types';
import {
  AdapterParsedTorrent,
  AdapterTorrent,
  AdapterTorrentWithInfo,
  TRACKER_TOKEN,
} from '../adapters.types';
import { NcoreClient } from './ncore.client';
import {
  MOVIE_CATEGORY_FILTERS,
  SERIES_CATEGORY_FILTERS,
} from './ncore.constants';
import {
  NcoreCategory,
  NcoreMovieCategoryEnum,
  NcoreSeriesCategoryEnum,
} from './ncore.types';

@Injectable()
export class NcoreAdapter implements TrackerAdapter {
  constructor(
    @Inject(TRACKER_TOKEN) readonly tracker: TrackerEnum,
    private client: NcoreClient,
  ) {}

  async login(payload: LoginRequest): Promise<void> {
    await this.client.login(payload);
  }

  async find(query: TrackerSearchQuery): Promise<AdapterTorrentWithInfo[]> {
    const { imdbId, mediaType } = query;

    let categories: NcoreCategory[] = [
      ...MOVIE_CATEGORY_FILTERS,
      ...SERIES_CATEGORY_FILTERS,
    ];

    if (mediaType === MediaTypeEnum.MOVIE) {
      categories = MOVIE_CATEGORY_FILTERS;
    }

    if (mediaType === MediaTypeEnum.SERIES) {
      categories = SERIES_CATEGORY_FILTERS;
    }

    const torrents = await this.client.find({ imdbId, categories });

    return torrents.map((torrent) => {
      const resolution = this.resolveTorrentResolution(torrent.category);
      const language = this.resolveVideoLanguage(torrent.category);

      return {
        tracker: this.tracker,
        imdbId: torrent.imdb_id,
        torrentId: torrent.torrent_id,
        seeders: Number(torrent.seeders),
        resolution,
        language,
        downloadUrl: torrent.download_url,
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
    category: NcoreMovieCategoryEnum | NcoreSeriesCategoryEnum,
  ): ResolutionEnum {
    switch (category) {
      case NcoreMovieCategoryEnum.SD:
      case NcoreMovieCategoryEnum.SD_HUN:
      case NcoreSeriesCategoryEnum.SD:
      case NcoreSeriesCategoryEnum.SD_HUN:
        return ResolutionEnum.R480P;

      case NcoreMovieCategoryEnum.HD:
      case NcoreMovieCategoryEnum.HD_HUN:
      case NcoreSeriesCategoryEnum.HD:
      case NcoreSeriesCategoryEnum.HD_HUN:
        return ResolutionEnum.R720P;
    }
  }

  private resolveVideoLanguage(
    category: NcoreMovieCategoryEnum | NcoreSeriesCategoryEnum,
  ): LanguageEnum {
    const huCategories = [
      NcoreMovieCategoryEnum.SD_HUN,
      NcoreMovieCategoryEnum.HD_HUN,
      NcoreSeriesCategoryEnum.SD_HUN,
      NcoreSeriesCategoryEnum.HD_HUN,
    ];

    if (huCategories.includes(category)) {
      return LanguageEnum.HU;
    } else {
      return LanguageEnum.EN;
    }
  }
}
