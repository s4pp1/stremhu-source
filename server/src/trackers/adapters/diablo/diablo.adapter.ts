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
import { DiabloClient } from './diablo.client';
import {
  DIABLO_MOVIE_CATEGORY_FILTERS,
  DIABLO_SERIES_CATEGORY_FILTERS,
} from './diablo.constants';
import {
  DiabloMovieCategoryEnum,
  DiabloSeriesCategoryEnum,
} from './diablo.types';

@Injectable()
export class DiabloAdapter implements TrackerAdapter {
  constructor(
    @Inject(TRACKER_TOKEN) readonly tracker: TrackerEnum,
    private client: DiabloClient,
  ) {}

  async login(payload: LoginRequest): Promise<void> {
    await this.client.login(payload);
  }

  async find(query: TrackerSearchQuery): Promise<AdapterTorrent[]> {
    const { imdbId, mediaType } = query;

    let categories: string[] = [
      ...DIABLO_MOVIE_CATEGORY_FILTERS,
      ...DIABLO_SERIES_CATEGORY_FILTERS,
    ];

    switch (mediaType) {
      case StreamMediaTypeEnum.MOVIE:
        categories = DIABLO_MOVIE_CATEGORY_FILTERS;
        break;

      case StreamMediaTypeEnum.SERIES:
        categories = DIABLO_SERIES_CATEGORY_FILTERS;
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

  async findOne(torrentId: string): Promise<AdapterTorrentId> {
    return this.client.findOne(torrentId);
  }

  async download(payload: AdapterTorrentId): Promise<AdapterParsedTorrent> {
    return this.client.download(payload);
  }

  async seedRequirement(): Promise<string[]> {
    return this.client.hitnrun();
  }

  private resolveTorrentResolution(
    category: DiabloMovieCategoryEnum | DiabloSeriesCategoryEnum,
  ): ResolutionEnum {
    switch (category) {
      case DiabloMovieCategoryEnum.SD:
      case DiabloMovieCategoryEnum.SD_HUN:
      case DiabloMovieCategoryEnum.CAM:
      case DiabloMovieCategoryEnum.CAM_HU:
      case DiabloSeriesCategoryEnum.SD:
      case DiabloSeriesCategoryEnum.SD_HUN:
        return ResolutionEnum.R480P;

      case DiabloMovieCategoryEnum.HD:
      case DiabloMovieCategoryEnum.HD_HUN:
      case DiabloSeriesCategoryEnum.HD:
      case DiabloSeriesCategoryEnum.HD_HUN:
        return ResolutionEnum.R720P;
    }
  }

  private resolveVideoLanguage(
    category: DiabloMovieCategoryEnum | DiabloSeriesCategoryEnum,
  ): LanguageEnum {
    const huCategories = [
      DiabloMovieCategoryEnum.SD_HUN,
      DiabloMovieCategoryEnum.HD_HUN,
      DiabloMovieCategoryEnum.CAM_HU,
      DiabloSeriesCategoryEnum.SD_HUN,
      DiabloSeriesCategoryEnum.HD_HUN,
    ];

    if (huCategories.includes(category)) {
      return LanguageEnum.HU;
    } else {
      return LanguageEnum.EN;
    }
  }
}
