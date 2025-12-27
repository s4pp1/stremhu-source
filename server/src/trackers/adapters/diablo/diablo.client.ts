import {
  Inject,
  Injectable,
  Logger,
  ServiceUnavailableException,
} from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import Bottleneck from 'bottleneck';
import { load } from 'cheerio';
import _ from 'lodash';

import { parseTorrent } from 'src/common/utils/parse-torrent.util';
import { TrackerEnum } from 'src/trackers/enum/tracker.enum';
import { TrackerToLogin } from 'src/trackers/type/tracker-to-login.type';

import {
  AdapterParsedTorrent,
  AdapterTorrentId,
  TRACKER_TOKEN,
} from '../adapters.types';
import {
  getTrackerStructureErrorMessage,
  getTrackerTorrentDownloadErrorMessage,
} from '../adapters.utils';
import { DiabloClientFactory } from './diablo.client-factory';
import {
  DIABLO_DETAILS_PATH,
  DIABLO_HIT_N_RUN_PATH,
  DIABLO_TORRENTS_PATH,
} from './diablo.constants';
import {
  DiabloCategory,
  DiabloTorrent,
  DiabloTorrents,
  DiabloTorrentsQuery,
} from './diablo.types';

@Injectable()
export class DiabloClient {
  private readonly logger = new Logger(DiabloClient.name);
  private readonly limiter: Bottleneck;

  private readonly baseUrl: string;

  constructor(
    @Inject(TRACKER_TOKEN) readonly tracker: TrackerEnum,
    private configService: ConfigService,
    private clientFactory: DiabloClientFactory,
  ) {
    this.baseUrl = this.configService.getOrThrow<string>('tracker.diablo-url');

    const maxConcurrent = this.configService.getOrThrow<number>(
      'tracker.diablo-max-concurrent',
    );

    this.limiter = new Bottleneck({
      maxConcurrent,
    });
  }

  login(payload: TrackerToLogin) {
    return this.requestLimit(() => this.clientFactory.login(payload));
  }

  find(payload: DiabloTorrentsQuery) {
    return this.findAll(payload);
  }

  private async findAll(
    payload: DiabloTorrentsQuery,
    page: number = 0,
    accumulator: DiabloTorrent[] = [],
  ): Promise<DiabloTorrent[]> {
    try {
      const { imdbId, categories } = payload;

      const torrentsUrl = new URL(DIABLO_TORRENTS_PATH, this.baseUrl);
      torrentsUrl.searchParams.append('genre', '0');
      torrentsUrl.searchParams.append('search', imdbId);
      torrentsUrl.searchParams.append('page', `${page}`);

      categories.forEach((category) => {
        torrentsUrl.searchParams.append(`c${category}`, '1');
      });

      const response = await this.requestLimit(() =>
        this.clientFactory.client.get<string>(torrentsUrl.href, {
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
      const detailsUrl = new URL(DIABLO_DETAILS_PATH, this.baseUrl);
      detailsUrl.searchParams.append('id', torrentId);

      const response = await this.requestLimit(() =>
        this.clientFactory.client.get<string>(detailsUrl.href),
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
      throw new ServiceUnavailableException(errorMessage);
    }
  }

  async download(payload: AdapterTorrentId): Promise<AdapterParsedTorrent> {
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
      const hitAndRunUrl = new URL(DIABLO_HIT_N_RUN_PATH, this.baseUrl);

      const response = await this.requestLimit(() =>
        this.clientFactory.client.get<string>(hitAndRunUrl.href, {
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
      throw new ServiceUnavailableException(errorMessage);
    }
  }

  private processTorrentsHtml(html: unknown): DiabloTorrents {
    if (typeof html !== 'string') {
      return {
        results: [],
        hasNextPage: false,
      };
    }

    const $ = load(html);
    const torrentRows = $('#torrenttable tbody tr').slice(1);
    const torrents: DiabloTorrent[] = torrentRows
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
          category: category as DiabloCategory,
          seeders: seeders,
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
