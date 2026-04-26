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
import { FilelistClient } from './filelist.client';
import {
  MOVIE_CATEGORY_FILTERS,
  SERIES_CATEGORY_FILTERS,
} from './filelist.constants';
import {
  FilelistCategory,
  FilelistMovieCategoryEnum,
  FilelistSeriesCategoryEnum,
} from './filelist.types';

@Injectable()
export class FilelistAdapter implements TrackerAdapter {
  constructor(
    @Inject(TRACKER_TOKEN) readonly tracker: TrackerEnum,
    private client: FilelistClient,
  ) { }

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
        imdbId,
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

  private resolveTorrentResolution(category: FilelistCategory): ResolutionEnum {
    switch (category) {
      case FilelistMovieCategoryEnum.SD:
      case FilelistMovieCategoryEnum.DVD:
      case FilelistSeriesCategoryEnum.TV:
      case FilelistSeriesCategoryEnum.SD:
        return ResolutionEnum.R480P;

      case FilelistMovieCategoryEnum.HD:
      case FilelistSeriesCategoryEnum.HD:
        return ResolutionEnum.R720P;

      case FilelistMovieCategoryEnum.BLU_RAY:
        return ResolutionEnum.R1080P;

      case FilelistMovieCategoryEnum.UHD:
      case FilelistMovieCategoryEnum.UHD_BLU_RAY:
      case FilelistSeriesCategoryEnum.UHD:
        return ResolutionEnum.R2160P;
    }
  }

  private resolveVideoLanguage(_category: FilelistCategory): LanguageEnum {
    return LanguageEnum.EN;
  }
}
