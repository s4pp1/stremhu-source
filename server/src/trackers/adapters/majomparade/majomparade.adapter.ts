import { Resolution as ResolutionEnum } from '@ctrl/video-filename-parser';
import { Inject, Injectable } from '@nestjs/common';

import { LanguageEnum } from 'src/common/enums/language.enum';
import { StreamMediaTypeEnum } from 'src/stremio/enums/stream-media-type.enum';
import { TrackerEnum } from 'src/trackers/enums/tracker.enum';
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
import { MajomparadeClient } from './majomparade.client';
import {
  MAJOMPARADE_MOVIE_CATEGORY_FILTERS,
  MAJOMPARADE_SERIES_CATEGORY_FILTERS,
} from './majomparade.constants';
import {
  MajomparadeMovieCategoryEnum,
  MajomparadeSeriesCategoryEnum,
} from './majomparade.types';

@Injectable()
export class MajomparadeAdapter implements TrackerAdapter {
  constructor(
    @Inject(TRACKER_TOKEN) readonly tracker: TrackerEnum,
    private majomparadeClient: MajomparadeClient,
  ) {}

  async login(payload: LoginRequest): Promise<void> {
    await this.majomparadeClient.login(payload);
  }

  async find(query: TrackerSearchQuery): Promise<AdapterTorrent[]> {
    const { imdbId, mediaType } = query;

    let categories: string[] = [];

    if (mediaType === StreamMediaTypeEnum.MOVIE) {
      categories = MAJOMPARADE_MOVIE_CATEGORY_FILTERS;
    }

    if (mediaType === StreamMediaTypeEnum.SERIES) {
      categories = MAJOMPARADE_SERIES_CATEGORY_FILTERS;
    }

    const torrents = await this.majomparadeClient.find({ imdbId, categories });

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
    return this.majomparadeClient.findOne(torrentId);
  }

  async download(payload: AdapterTorrentId): Promise<AdapterParsedTorrent> {
    return this.majomparadeClient.download(payload);
  }

  async seedRequirement(): Promise<string[]> {
    return this.majomparadeClient.hitnrun();
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
