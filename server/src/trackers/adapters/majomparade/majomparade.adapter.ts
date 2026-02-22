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
import { MajomparadeClient } from './majomparade.client';
import {
  MOVIE_CATEGORY_FILTERS,
  SERIES_CATEGORY_FILTERS,
} from './majomparade.constants';
import {
  MajomparadeMovieCategoryEnum,
  MajomparadeSeriesCategoryEnum,
} from './majomparade.types';

@Injectable()
export class MajomparadeAdapter implements TrackerAdapter {
  constructor(
    @Inject(TRACKER_TOKEN) readonly tracker: TrackerEnum,
    private client: MajomparadeClient,
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
    category: MajomparadeMovieCategoryEnum | MajomparadeSeriesCategoryEnum,
  ): ResolutionEnum {
    switch (category) {
      case MajomparadeMovieCategoryEnum.CAM:
      case MajomparadeMovieCategoryEnum.CAM_HUN:
      case MajomparadeMovieCategoryEnum.SD:
      case MajomparadeMovieCategoryEnum.SD_HUN:
      case MajomparadeSeriesCategoryEnum.SD:
      case MajomparadeSeriesCategoryEnum.SD_HUN:
        return ResolutionEnum.R480P;

      case MajomparadeMovieCategoryEnum.HD:
      case MajomparadeMovieCategoryEnum.HD_HUN:
      case MajomparadeSeriesCategoryEnum.HD:
      case MajomparadeSeriesCategoryEnum.HD_HUN:
        return ResolutionEnum.R720P;
    }
  }

  private resolveVideoLanguage(
    category: MajomparadeMovieCategoryEnum | MajomparadeSeriesCategoryEnum,
  ): LanguageEnum {
    const huCategories = [
      MajomparadeMovieCategoryEnum.CAM_HUN,
      MajomparadeMovieCategoryEnum.SD_HUN,
      MajomparadeMovieCategoryEnum.HD_HUN,
      MajomparadeSeriesCategoryEnum.SD_HUN,
      MajomparadeSeriesCategoryEnum.HD_HUN,
    ];

    if (huCategories.includes(category)) {
      return LanguageEnum.HU;
    } else {
      return LanguageEnum.EN;
    }
  }
}
