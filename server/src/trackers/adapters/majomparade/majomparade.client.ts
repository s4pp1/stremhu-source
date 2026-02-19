import {
  Inject,
  Injectable,
  Logger,
  ServiceUnavailableException,
} from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import Bottleneck from 'bottleneck';
import { load } from 'cheerio';
import { compact, nth } from 'lodash';

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

      const unixSeconds = Math.floor(Date.now() / 1000);

      torrentsUrl.searchParams.append('tipus', '1');
      torrentsUrl.searchParams.append('time', `${unixSeconds}`);
      torrentsUrl.searchParams.append('k', 'yes');
      torrentsUrl.searchParams.append('tipuska', '0');
      torrentsUrl.searchParams.append(
        'name',
        `https://www.imdb.com/title/${imdbId}/`,
      );
      torrentsUrl.searchParams.append('imdb_search', 'yes');
      torrentsUrl.searchParams.append('page', `${page}`);

      categories.forEach((category) => {
        torrentsUrl.searchParams.append(`category[]`, `${category}`);
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
      throw new ServiceUnavailableException(errorMessage);
    }
  }

  async findOne(torrentId: string): Promise<AdapterTorrentId> {
    try {
      const detailsPath = DETAILS_PATH.replace('{torrentId}', torrentId);
      const detailsUrl = new URL(detailsPath, this.baseUrl);

      const response = await this.requestLimit(() =>
        this.majomparadeClientFactory.client.get<string>(detailsUrl.href, {
          responseType: 'text',
        }),
      );

      const $ = load(response.data);

      const downloadPath = $(`a[href*="download.php?torrent=${torrentId}"]`)
        .first()
        .attr('href');
      const imdbUrl =
        $('a[href*="www.imdb.com/title/"]').first().attr('href') || '';

      const imdbId = nth(imdbUrl.split('/'), -2);

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
      throw new ServiceUnavailableException(errorMessage);
    }
  }

  async download(payload: AdapterTorrentId): Promise<AdapterParsedTorrent> {
    const { torrentId, downloadUrl } = payload;

    try {
      const response = await this.requestLimit(() =>
        this.majomparadeClientFactory.client.get<ArrayBuffer>(downloadUrl, {
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
      throw new ServiceUnavailableException(errorMessage);
    }
  }

  private processTorrentsHtml(html: string): MajomparadeTorrents {
    const $ = load(html);
    const torrentRows = $('#table tbody tr').slice(1);

    const torrents: MajomparadeTorrent[] = [];

    torrentRows
      .each((_, torrentRow) => {
        const torrentColumns = $(torrentRow).children('td');

        const CATEGORY_URL = 'letoltes.php?k=yes&tipus=1&category[]=';
        const categoryHref = torrentColumns
          .eq(0)
          .find(`a[href*="${CATEGORY_URL}"]`)
          .attr('href');
        if (!categoryHref) return;

        const downloadPath = torrentColumns
          .find(`a[href*="download.php?torrent="]`)
          .first()
          .attr('href');
        if (!downloadPath) return;

        const torrentId = `${downloadPath}`.replace(
          'download.php?torrent=',
          '',
        );

        const seeders = torrentColumns.eq(8).text();

        const categoryId = categoryHref.replace(CATEGORY_URL, '');
        const downloadUrl = new URL(downloadPath, this.baseUrl);

        torrents.push({
          torrentId,
          downloadUrl: downloadUrl.href,
          category: categoryId as MajomparadeCategory,
          seeders: seeders,
        });
      })
      .get();

    const nextLink = $('p b')
      .filter((_, el) => $(el).text().includes('Következő >>'))
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
