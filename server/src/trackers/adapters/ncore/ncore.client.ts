import { Inject, Injectable, Logger } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import Bottleneck from 'bottleneck';
import { load } from 'cheerio';
import { compact, last } from 'lodash';

import { parseTorrent } from 'src/common/utils/parse-torrent.util';
import { TrackerEnum } from 'src/trackers/enum/tracker.enum';

import { FIND_TORRENTS_LIMIT } from '../adapter.contant';
import {
  AdapterLoginRequest,
  AdapterParsedTorrent,
  AdapterTorrentId,
  TRACKER_TOKEN,
} from '../adapters.types';
import {
  getTrackerStructureErrorMessage,
  getTrackerTorrentDownloadErrorMessage,
} from '../adapters.utils';
import { NcoreClientFactory } from './ncore.client-factory';
import { DETAILS_PATH, HIT_N_RUN_PATH, TORRENTS_PATH } from './ncore.constants';
import {
  NcoreDownloadRequest,
  NcoreFindQuery,
  NcoreOrderByEnum,
  NcoreOrderDirectionEnum,
  NcoreSearchByEnum,
  NcoreSearchParams,
  NcoreSearchTypeEnum,
  NcoreTorrent,
  NcoreTorrents,
} from './ncore.types';

@Injectable()
export class NcoreClient {
  private readonly logger = new Logger(NcoreClient.name);
  private readonly limiter: Bottleneck;
  private readonly baseUrl: string;

  constructor(
    @Inject(TRACKER_TOKEN) private readonly tracker: TrackerEnum,
    private configService: ConfigService,
    private clientFactory: NcoreClientFactory,
  ) {
    this.baseUrl = this.configService.getOrThrow<string>('tracker.ncore-url');

    const maxConcurrent = this.configService.getOrThrow<number>(
      'tracker.ncore-max-concurrent',
    );

    this.limiter = new Bottleneck({
      maxConcurrent,
    });
  }

  login(payload: AdapterLoginRequest) {
    return this.requestLimit(() => this.clientFactory.login(payload));
  }

  async find(payload: NcoreFindQuery): Promise<NcoreTorrent[]> {
    return this.findAll(payload);
  }

  private async findAll(
    payload: NcoreFindQuery,
    page: number = 1,
    accumulator: NcoreTorrent[] = [],
  ): Promise<NcoreTorrent[]> {
    if (accumulator.length > FIND_TORRENTS_LIMIT) {
      return accumulator;
    }

    try {
      const { imdbId, categories } = payload;

      const torrentsUrl = new URL(TORRENTS_PATH, this.baseUrl);

      const searchParams: NcoreSearchParams = {
        oldal: page,
        miben: NcoreSearchByEnum.IMDB,
        mire: imdbId,
        miszerint: NcoreOrderByEnum.SEEDERS,
        hogyan: NcoreOrderDirectionEnum.DESC,
        tipus: NcoreSearchTypeEnum.SELECTED,
        kivalasztott_tipus: categories,
        jsons: true,
      };

      const response = await this.requestLimit(() =>
        this.clientFactory.client.get<NcoreTorrents | string>(
          torrentsUrl.href,
          {
            params: searchParams,
          },
        ),
      );

      if (typeof response.data === 'string') {
        const $ = load(response.data);
        const errorText = $('.lista_mini_error').first().text();

        if (errorText === 'Nincs találat!') {
          return accumulator;
        }

        throw new Error(errorText);
      }

      accumulator = [...accumulator, ...response.data.results];

      const total = Number(response.data.total_results);
      const limit = Number(response.data.perpage);
      const lastPage = Math.ceil(total / limit);

      if (lastPage > page) {
        return this.findAll(payload, page + 1, accumulator);
      }

      return accumulator;
    } catch (error) {
      const errorMessage = getTrackerStructureErrorMessage(this.tracker);
      this.logger.error(errorMessage, error);
      throw new Error(errorMessage);
    }
  }

  async findOne(torrentId: string): Promise<AdapterTorrentId> {
    try {
      const detailsPath = DETAILS_PATH.replace('{torrentId}', torrentId);
      const detailsUrl = new URL(detailsPath, this.baseUrl);

      const response = await this.requestLimit(() =>
        this.clientFactory.client.get<string>(detailsUrl.href),
      );

      const $ = load(response.data);

      const downloadPath = $(
        `.download a[href*="torrents.php?action=download&id=${torrentId}"]`,
      )
        .first()
        .attr('href');

      const imdbUrl = $('a[href*=https://imdb.com/title/]').first().text();

      const imdbId = last(imdbUrl.split('/'));

      if (!downloadPath || !imdbId) {
        throw new Error(
          `"downloadPath": ${downloadPath} vagy "imdbId": ${imdbId} nem található`,
        );
      }

      const downloadUrl = new URL(downloadPath, this.baseUrl);

      return {
        tracker: this.tracker,
        torrentId,
        imdbId,
        downloadUrl: downloadUrl.href,
      };
    } catch (error) {
      const errorMessage = getTrackerStructureErrorMessage(this.tracker);
      this.logger.error(errorMessage, error);
      throw new Error(errorMessage);
    }
  }

  async download(payload: NcoreDownloadRequest): Promise<AdapterParsedTorrent> {
    const { torrentId, downloadUrl } = payload;

    try {
      const response = await this.requestLimit(() =>
        this.clientFactory.client.get<ArrayBuffer>(downloadUrl, {
          responseType: 'arraybuffer',
        }),
      );

      const bytes = new Uint8Array(response.data);
      const parsed = await parseTorrent(bytes);

      return { torrentId, parsed };
    } catch (error) {
      this.logger.error(
        getTrackerTorrentDownloadErrorMessage(this.tracker, torrentId),
        error,
      );

      throw error;
    }
  }

  async hitnrun(): Promise<string[]> {
    try {
      const hitAndRunUrl = new URL(HIT_N_RUN_PATH, this.baseUrl);
      hitAndRunUrl.searchParams.append('showall', 'false');

      const response = await this.requestLimit(() =>
        this.clientFactory.client.get<string>(hitAndRunUrl.href, {
          responseType: 'text',
        }),
      );

      const $ = load(response.data);

      const hitnrunTorrents = $(
        '.box_torrent_all a[href*="torrents.php?action=details&id="]',
      )
        .map((_, el) => $(el).attr('href'))
        .get();

      const sourceIds = hitnrunTorrents.map((hitnrunTorrent) => {
        const url = new URL(hitnrunTorrent, this.baseUrl);
        const idParam = url.searchParams.get('id');
        return idParam;
      });

      return compact(sourceIds);
    } catch (error) {
      const errorMessage = getTrackerStructureErrorMessage(this.tracker);
      this.logger.error(errorMessage, error);
      throw new Error(errorMessage);
    }
  }

  private requestLimit<T>(fn: () => Promise<T>) {
    return this.limiter.schedule(fn);
  }
}
