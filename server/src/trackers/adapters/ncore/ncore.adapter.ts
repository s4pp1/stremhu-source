import { Resolution as ResolutionEnum } from '@ctrl/video-filename-parser';
import { Inject, Injectable } from '@nestjs/common';

import { LanguageEnum } from 'src/common/enums/language.enum';

import { TrackerEnum } from '../../enums/tracker.enum';
import {
  LoginRequest,
  TrackerAdapter,
  TrackerSearchQuery,
} from '../../tracker.types';
import {
  AdapterParsedTorrent,
  AdapterTorrent,
  AdapterTorrentId,
  TRACKER_TOKEN,
} from '../adapters.types';
import { NcoreClient } from './ncore.client';
import { NcoreMovieCategoryEnum, NcoreSeriesCategoryEnum } from './ncore.types';

@Injectable()
export class NcoreAdapter implements TrackerAdapter {
  constructor(
    @Inject(TRACKER_TOKEN) readonly tracker: TrackerEnum,
    private ncoreClient: NcoreClient,
  ) {}

  async login(payload: LoginRequest): Promise<void> {
    await this.ncoreClient.login(payload);
  }

  async find(query: TrackerSearchQuery): Promise<AdapterTorrent[]> {
    const torrents = await this.ncoreClient.torrents(query);

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

  async findOne(torrentId: string): Promise<AdapterTorrentId> {
    return this.ncoreClient.findOneTorrent(torrentId);
  }

  async download(payload: AdapterTorrentId): Promise<AdapterParsedTorrent> {
    return this.ncoreClient.download(payload);
  }

  async seedRequirement(): Promise<string[]> {
    return this.ncoreClient.hitnrun();
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
