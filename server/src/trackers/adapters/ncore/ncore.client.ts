import { Injectable, NotFoundException } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { load } from 'cheerio';
import _ from 'lodash';

import { parseTorrent } from 'src/common/utils/parse-torrent.util';
import { StreamMediaTypeEnum } from 'src/stremio/enums/stream-media-type.enum';
import { TrackerEnum } from 'src/trackers/enums/tracker.enum';

import { AdapterParsedTorrent, AdapterTorrentId } from '../adapters.types';
import { NcoreClientFactory } from './ncore.client-factory';
import {
  NCORE_DOWNLOAD_PATH,
  NCORE_HIT_N_RUN_PATH,
  NCORE_MOVIE_CATEGORY_FILTERS,
  NCORE_SERIES_CATEGORY_FILTERS,
  NCORE_TORRENTS_PATH,
} from './ncore.constants';
import {
  NcoreCategory,
  NcoreDownloadRequest,
  NcoreLoginRequest,
  NcoreOrderByEnum,
  NcoreOrderDirectionEnum,
  NcoreSearchByEnum,
  NcoreSearchParams,
  NcoreSearchQuery,
  NcoreSearchTypeEnum,
  NcoreTorrent,
  NcoreTorrents,
} from './ncore.types';

@Injectable()
export class NcoreClient {
  private readonly ncoreBaseUrl: string;

  constructor(
    private configService: ConfigService,
    private ncoreClientFactory: NcoreClientFactory,
  ) {
    this.ncoreBaseUrl =
      this.configService.getOrThrow<string>('tracker.ncore-url');
  }

  login(payload: NcoreLoginRequest) {
    return this.ncoreClientFactory.login(payload, true);
  }

  async getTorrents(query: NcoreSearchQuery): Promise<NcoreTorrents> {
    const { mediaType, imdbId, page = 1 } = query;

    const url = new URL(NCORE_TORRENTS_PATH, this.ncoreBaseUrl).toString();

    let kivalasztott_tipus: Array<NcoreCategory> = [];

    if (mediaType === StreamMediaTypeEnum.MOVIE) {
      kivalasztott_tipus = NCORE_MOVIE_CATEGORY_FILTERS;
    }

    if (mediaType === StreamMediaTypeEnum.SERIES) {
      kivalasztott_tipus = NCORE_SERIES_CATEGORY_FILTERS;
    }

    const searchParams: NcoreSearchParams = {
      oldal: page,
      miben: NcoreSearchByEnum.IMDB,
      mire: imdbId,
      miszerint: NcoreOrderByEnum.SEEDERS,
      hogyan: NcoreOrderDirectionEnum.DESC,
      tipus: NcoreSearchTypeEnum.SELECTED,
      kivalasztott_tipus,
      jsons: true,
    };

    const response = await this.ncoreClientFactory.client.get<
      NcoreTorrents | string
    >(url, {
      params: searchParams,
    });

    if (typeof response.data === 'string') {
      return {
        total_results: '0',
        onpage: 0,
        perpage: '0',
        results: [],
      };
    }

    return response.data;
  }

  async torrents(
    query: NcoreSearchQuery,
    accumulator: NcoreTorrent[] = [],
  ): Promise<NcoreTorrent[]> {
    const response = await this.getTorrents(query);
    accumulator = [...accumulator, ...response.results];

    const { page = 1 } = query;

    const total = Number(response.total_results);
    const limit = Number(response.perpage);
    const lastPage = Math.ceil(total / limit);

    if (lastPage > page) {
      query.page = page + 1;
      return this.torrents(query, accumulator);
    }

    return accumulator;
  }

  async download(payload: NcoreDownloadRequest): Promise<AdapterParsedTorrent> {
    const { torrentId, downloadUrl } = payload;

    const response = await this.ncoreClientFactory.client.get<ArrayBuffer>(
      downloadUrl,
      {
        responseType: 'arraybuffer',
      },
    );

    const bytes = new Uint8Array(response.data);
    const parsed = await parseTorrent(bytes);

    return { torrentId, parsed };
  }

  async findOneTorrent(torrentId: string): Promise<AdapterTorrentId> {
    const url = new URL(NCORE_DOWNLOAD_PATH, this.ncoreBaseUrl);

    url.searchParams.append('action', 'details');
    url.searchParams.append('id', torrentId);

    const response = await this.ncoreClientFactory.client.get<string>(
      url.toString(),
    );

    const $ = load(response.data);

    const ncoreDownloadPath = $('.download').first().find('a').attr('href');
    const imdbUrl = $('.inforbar_txt tr')
      .filter((_, el) => $(el).text().includes('IMDb link:'))
      .first()
      .find('td')
      .eq(1)
      .find('a')
      .text();

    const imdbId = _.last(imdbUrl.split('/'));

    if (!ncoreDownloadPath || !imdbId) {
      throw new NotFoundException('nCore torrent adatlapja nem található');
    }

    const downloadUrl = new URL(
      ncoreDownloadPath,
      this.ncoreBaseUrl,
    ).toString();

    return {
      tracker: TrackerEnum.NCORE,
      torrentId,
      imdbId,
      downloadUrl,
    };
  }

  /**
   * Visszaadja a “hit & run” nCore torrentek azonosítóit.
   */
  async hitnrun(): Promise<string[]> {
    const url = new URL(NCORE_HIT_N_RUN_PATH, this.ncoreBaseUrl).toString();

    const response = await this.ncoreClientFactory.client.get<string>(url, {
      responseType: 'text',
    });

    const $ = load(response.data);

    const hitnrunTorrents = $('.box_torrent_all')
      .find('.hnr_torrents a')
      .map((_, el) => $(el).attr('href'))
      .get();

    const sourceIds = hitnrunTorrents.map((hitnrunTorrent) => {
      const url = new URL(hitnrunTorrent, this.ncoreBaseUrl);
      const idParam = url.searchParams.get('id');
      return idParam;
    });

    return _.compact(sourceIds);
  }
}
