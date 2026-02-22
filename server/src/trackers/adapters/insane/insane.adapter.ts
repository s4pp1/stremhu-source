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
import { InsaneClient } from './insane.client';
import {
  MOVIE_CATEGORY_FILTERS,
  SERIES_CATEGORY_FILTERS,
} from './insane.constants';
import {
  CategoryEnum,
  MovieCategoryEnum,
  SeriesCategoryEnum,
} from './insane.types';

@Injectable()
export class InsaneAdapter implements TrackerAdapter {
  constructor(
    @Inject(TRACKER_TOKEN) readonly tracker: TrackerEnum,
    private client: InsaneClient,
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

  private resolveTorrentResolution(category: CategoryEnum): ResolutionEnum {
    switch (category) {
      case MovieCategoryEnum.SD:
      case MovieCategoryEnum.SD_HUN:
      case SeriesCategoryEnum.SD:
      case SeriesCategoryEnum.SD_HUN:
        return ResolutionEnum.R480P;

      case MovieCategoryEnum.HD:
      case MovieCategoryEnum.HD_HUN:
      case SeriesCategoryEnum.HD:
      case SeriesCategoryEnum.HD_HUN:
        return ResolutionEnum.R720P;

      case MovieCategoryEnum.UHD:
      case MovieCategoryEnum.UHD_HUN:
      case SeriesCategoryEnum.UHD:
      case SeriesCategoryEnum.UHD_HUN:
        return ResolutionEnum.R2160P;
    }
  }

  private resolveVideoLanguage(category: CategoryEnum): LanguageEnum {
    const huCategories = [
      MovieCategoryEnum.SD_HUN,
      MovieCategoryEnum.HD_HUN,
      MovieCategoryEnum.UHD_HUN,
      SeriesCategoryEnum.SD_HUN,
      SeriesCategoryEnum.HD_HUN,
      SeriesCategoryEnum.UHD_HUN,
    ];

    if (huCategories.includes(category)) {
      return LanguageEnum.HU;
    } else {
      return LanguageEnum.EN;
    }
  }
}
