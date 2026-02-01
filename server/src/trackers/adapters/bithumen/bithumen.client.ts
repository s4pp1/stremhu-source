import { Inject, Injectable, Logger } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import Bottleneck from 'bottleneck';
import { load } from 'cheerio';
import _, { nth } from 'lodash';

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
import { BithumenClientFactory } from './bithumen.client-factory';
import {
  DETAILS_PATH,
  HIT_N_RUN_PATH,
  TORRENTS_PATH,
} from './bithumen.constants';
import {
  BithumenCategory,
  BithumenTorrent,
  BithumenTorrents,
  BithumenTorrentsQuery,
} from './bithumen.types';

@Injectable()
export class BithumenClient {
  private readonly logger = new Logger(BithumenClient.name);
  private readonly limiter: Bottleneck;

  private readonly baseUrl: string;

  constructor(
    @Inject(TRACKER_TOKEN) readonly tracker: TrackerEnum,
    private configService: ConfigService,
    private bithumenClientFactory: BithumenClientFactory,
  ) {
    this.baseUrl = this.configService.getOrThrow<string>(
      'tracker.bithumen-url',
    );

    const maxConcurrent = this.configService.getOrThrow<number>(
      'tracker.bithumen-max-concurrent',
    );

    this.limiter = new Bottleneck({
      maxConcurrent,
    });
  }

  login(payload: AdapterLoginRequest) {
    return this.requestLimit(() => this.bithumenClientFactory.login(payload));
  }

  find(payload: BithumenTorrentsQuery) {
    return this.findAll(payload);
  }

  private async findAll(
    payload: BithumenTorrentsQuery,
    page: number = 0,
    accumulator: BithumenTorrent[] = [],
  ): Promise<BithumenTorrent[]> {
    if (accumulator.length > FIND_TORRENTS_LIMIT) {
      return accumulator;
    }

    try {
      const { imdbId, categories } = payload;

      const torrentsUrl = new URL(TORRENTS_PATH, this.baseUrl);
      torrentsUrl.searchParams.append('genre', '0');
      torrentsUrl.searchParams.append('search', imdbId);
      torrentsUrl.searchParams.append('page', `${page}`);

      categories.forEach((category) => {
        torrentsUrl.searchParams.append(`c${category}`, '1');
      });

      const response = await this.requestLimit(() =>
        this.bithumenClientFactory.client.get<string>(torrentsUrl.href, {
          responseType: 'text',
        }),
      );

      const data = this.processTorrentsHtml(response.data);

      accumulator = [...accumulator, ...data.results];

      if (data.hasNextPage) {
        return this.findAll(payload, page + 1, accumulator);
      }

      return accumulator.filter((acc) => acc.imdbId === imdbId);
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
        this.bithumenClientFactory.client.get<string>(detailsUrl.href),
      );

      const $ = load(response.data);

      const downloadPath = $(`a[href*="download.php/${torrentId}"]`)
        .first()
        .attr('href');
      const imdbUrl =
        $('a[href*="www.imdb.com/title/"]').first().attr('href') || '';

      const imdbId = _.nth(imdbUrl.split('/'), -2);

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

  async download(payload: AdapterTorrentId): Promise<AdapterParsedTorrent> {
    const { torrentId, downloadUrl } = payload;

    try {
      const response = await this.requestLimit(() =>
        this.bithumenClientFactory.client.get<ArrayBuffer>(downloadUrl, {
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
      const userId = await this.requestLimit(() =>
        this.bithumenClientFactory.getUserId(),
      );

      const hitAndRunUrl = new URL(HIT_N_RUN_PATH, this.baseUrl);
      hitAndRunUrl.searchParams.append('id', userId);
      hitAndRunUrl.searchParams.append('hnr', '1');

      const response = await this.requestLimit(() =>
        this.bithumenClientFactory.client.get<string>(hitAndRunUrl.href, {
          responseType: 'text',
        }),
      );

      const $ = load(response.data);
      const hitnrunTorrents = $('td a[href*="/details.php?id="]');
      const torrentIds = hitnrunTorrents
        .map((_, el) => $(el).attr('href'))
        .get();

      const sourceIds = torrentIds.map((hitnrunTorrent) => {
        const url = new URL(hitnrunTorrent, this.baseUrl);
        const idParam = url.searchParams.get('id');
        return idParam;
      });

      return _.compact(sourceIds);
    } catch (error) {
      const errorMessage = getTrackerStructureErrorMessage(this.tracker);
      this.logger.error(errorMessage, error);
      throw new Error(errorMessage);
    }
  }

  private processTorrentsHtml(html: unknown): BithumenTorrents {
    if (typeof html !== 'string') {
      return {
        results: [],
        hasNextPage: false,
      };
    }

    const $ = load(html);
    const torrentRows = $('#torrenttable tbody tr').slice(1);
    const torrents: BithumenTorrent[] = torrentRows
      .map((_, torrentRow) => {
        const torrentColumns = $(torrentRow).children('td');

        const categoryHref = torrentColumns.eq(0).find('a').attr('href') || '';
        const category = categoryHref.replace('?cat=', '');

        const downloadPath = torrentColumns
          .eq(1)
          .children('a')
          .eq(1)
          .attr('href')!;
        const downloadUrl = new URL(downloadPath, this.baseUrl);
        const imdbUrl =
          torrentColumns
            .eq(1)
            .find('a[href*="www.imdb.com/title/"]')
            .first()
            .attr('href') || '';
        const imdbId = nth(imdbUrl.split('/'), -2);

        const torrentId = torrentColumns
          .eq(1)
          .children('a')
          .eq(0)
          .attr('href')!
          .replace('details.php?id=', '');

        const seeders = torrentColumns.eq(7).text();

        return {
          torrentId,
          downloadUrl: downloadUrl.href,
          category: category as BithumenCategory,
          seeders: seeders,
          imdbId: imdbId || '',
        };
      })
      .get();

    const nextLink = $('#pagertop b')
      .filter((_, el) => $(el).text().includes('Tov�bb >>'))
      .first();

    const hasNextPage = nextLink.length > 0 && nextLink.parent().is('a');

    return {
      results: torrents,
      hasNextPage,
    };
  }

  private requestLimit<T>(fn: () => Promise<T>) {
    return this.limiter.schedule(fn);
  }
}
