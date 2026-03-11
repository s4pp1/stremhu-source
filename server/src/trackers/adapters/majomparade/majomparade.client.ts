import { Inject, Injectable, Logger } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import Bottleneck from 'bottleneck';
import { load } from 'cheerio';
import { compact, nth } from 'lodash';

import { TrackerEnum } from 'src/trackers/enum/tracker.enum';

import { FIND_TORRENTS_LIMIT } from '../adapter.contant';
import {
  AdapterLoginRequest,
  AdapterParsedTorrent,
  AdapterTorrent,
  TRACKER_TOKEN,
} from '../adapters.types';
import {
  getTrackerStructureErrorMessage,
  getTrackerTorrentDownloadErrorMessage,
} from '../adapters.utils';
import { MajomparadeClientFactory } from './majomparade.client-factory';
import {
  DETAILS_PATH,
  HIT_N_RUN_PATH,
  TORRENTS_PATH,
} from './majomparade.constants';
import {
  MajomparadeCategory,
  MajomparadeTorrent,
  MajomparadeTorrents,
  MajomparadeTorrentsQuery,
} from './majomparade.types';

@Injectable()
export class MajomparadeClient {
  private readonly logger = new Logger(MajomparadeClient.name);
  private readonly limiter: Bottleneck;

  private readonly baseUrl: string;

  constructor(
    @Inject(TRACKER_TOKEN) private readonly tracker: TrackerEnum,
    private configService: ConfigService,
    private majomparadeClientFactory: MajomparadeClientFactory,
  ) {
    this.baseUrl = this.configService.getOrThrow<string>(
      'tracker.majomparade-url',
    );

    const maxConcurrent = this.configService.getOrThrow<number>(
      'tracker.majomparade-max-concurrent',
    );

    this.limiter = new Bottleneck({
      maxConcurrent,
    });
  }

  login(payload: AdapterLoginRequest) {
    return this.requestLimit(() =>
      this.majomparadeClientFactory.login(payload),
    );
  }

  find(payload: MajomparadeTorrentsQuery) {
    return this.findAll(payload);
  }

  private async findAll(
    payload: MajomparadeTorrentsQuery,
    page: number = 0,
    accumulator: MajomparadeTorrent[] = [],
  ): Promise<MajomparadeTorrent[]> {
    try {
      if (accumulator.length > FIND_TORRENTS_LIMIT) {
        return accumulator;
      }

      const { imdbId, categories } = payload;

      const torrentsUrl = new URL(TORRENTS_PATH, this.baseUrl);

      torrentsUrl.searchParams.append('action', 'search');
      torrentsUrl.searchParams.append('search_text', imdbId);
      torrentsUrl.searchParams.append('sort', '5');
      torrentsUrl.searchParams.append('order_by', '0');
      torrentsUrl.searchParams.append('page', `${page}`);

      categories.forEach((category) => {
        torrentsUrl.searchParams.append(`categories[]`, `${category}`);
      });

      const response = await this.requestLimit(() =>
        this.majomparadeClientFactory.client.get<string>(torrentsUrl.href, {
          responseType: 'text',
        }),
      );

      const data = this.processTorrentsHtml(response.data);

      accumulator = [...accumulator, ...data.results];

      if (data.hasNextPage) {
        return this.findAll(payload, page + 1, accumulator);
      }

      return accumulator;
    } catch (error) {
      const errorMessage = getTrackerStructureErrorMessage(this.tracker);
      this.logger.error(errorMessage, error);
      throw new Error(errorMessage, { cause: error });
    }
  }

  async findOne(torrentId: string): Promise<AdapterTorrent> {
    try {
      const detailsPath = DETAILS_PATH.replace('{torrentId}', torrentId);
      const detailsUrl = new URL(detailsPath, this.baseUrl);

      const response = await this.requestLimit(() =>
        this.majomparadeClientFactory.client.get<string>(detailsUrl.href, {
          responseType: 'text',
        }),
      );

      const $ = load(response.data);

      const downloadPath = $(`form[action*="/download/${torrentId}"]`)
        .first()
        .attr('action');
      const imdbUrl =
        $('a[href*="www.imdb.com/title/"]').first().attr('href') || '';

      const imdbId = nth(imdbUrl.split('/'), -2);

      if (!downloadPath) {
        throw new Error(`A "downloadPath" nem található!`);
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
      throw new Error(errorMessage, { cause: error });
    }
  }

  async download(payload: AdapterTorrent): Promise<AdapterParsedTorrent> {
    const { torrentId, downloadUrl } = payload;

    try {
      const response = await this.requestLimit(() =>
        this.majomparadeClientFactory.client.get<ArrayBuffer>(downloadUrl, {
          responseType: 'arraybuffer',
        }),
      );

      const torrentBuffer = Buffer.from(response.data);

      return { torrentId, torrentBuffer };
    } catch (error) {
      this.logger.error(
        getTrackerTorrentDownloadErrorMessage(this.tracker, torrentId),
        error,
      );

      throw error;
    }
  }

  async hitnrun(): Promise<string[]> {
    throw new Error(`Az új oldalon a HnR még nem érhető el!`);

    try {
      const hitAndRunUrl = new URL(HIT_N_RUN_PATH, this.baseUrl);

      const response = await this.requestLimit(() =>
        this.majomparadeClientFactory.client.get<string>(hitAndRunUrl.href, {
          responseType: 'text',
        }),
      );

      const $ = load(response.data);

      const hitnrunTorrents = $('.also td a[href*="details.php?id="]')
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
      throw new Error(errorMessage, { cause: error });
    }
  }

  private processTorrentsHtml(html: string): MajomparadeTorrents {
    const $ = load(html);
    const torrentRows = $('article.torrent-card');

    const torrents: MajomparadeTorrent[] = [];

    torrentRows
      .each((_, torrentRow) => {
        const CATEGORY_URL = '/torrents/?action=search&categories[]=';
        const categoryHref = $(torrentRow)
          .find(`a[href*="${CATEGORY_URL}"]`)
          .first()
          .attr('href');
        if (!categoryHref) return;

        const categoryId = categoryHref.replace(CATEGORY_URL, '');

        const DOWNLOAD_URL = '/download/';
        const downloadPath = $(torrentRow)
          .find(`a[href*="${DOWNLOAD_URL}"]`)
          .first()
          .attr('href');
        if (!downloadPath) return;

        const torrentId = `${downloadPath}`.replace(DOWNLOAD_URL, '');

        const downloadUrl = new URL(downloadPath, this.baseUrl);

        const seeders = $(torrentRow)
          .find('.torrent-card__side .t-stats a')
          .eq(0)
          .text()
          .trim();

        torrents.push({
          torrentId,
          downloadUrl: downloadUrl.href,
          category: categoryId as MajomparadeCategory,
          seeders: seeders,
        });
      })
      .get();

    const nextPageButton = $('.pagination').first().last();
    const isDisabled = nextPageButton.hasClass('disabled');

    const hasNextPage = nextPageButton.length > 0 && !isDisabled;

    return {
      results: torrents,
      hasNextPage,
    };
  }

  private requestLimit<T>(fn: () => Promise<T>) {
    return this.limiter.schedule(fn);
  }
}
