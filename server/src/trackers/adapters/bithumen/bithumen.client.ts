import {
  Inject,
  Injectable,
  Logger,
  ServiceUnavailableException,
} from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { load } from 'cheerio';
import _ from 'lodash';

import { parseTorrent } from 'src/common/utils/parse-torrent.util';
import { TrackerEnum } from 'src/trackers/enums/tracker.enum';

import {
  AdapterParsedTorrent,
  AdapterTorrentId,
  TRACKER_TOKEN,
} from '../adapters.types';
import { getTrackerStructureErrorMessage } from '../adapters.utils';
import { BithumenClientFactory } from './bithumen.client-factory';
import {
  BITHUMEN_DETAILS_PATH,
  BITHUMEN_HIT_N_RUN_PATH,
  BITHUMEN_TORRENTS_PATH,
} from './bithumen.constants';
import {
  BithumenCategory,
  BithumenLoginRequest,
  BithumenTorrent,
  BithumenTorrents,
  BithumenTorrentsQuery,
} from './bithumen.types';

@Injectable()
export class BithumenClient {
  private readonly logger = new Logger(BithumenClient.name);
  private readonly bithumenBaseUrl: string;

  constructor(
    @Inject(TRACKER_TOKEN) readonly tracker: TrackerEnum,
    private configService: ConfigService,
    private bithumenClientFactory: BithumenClientFactory,
  ) {
    this.bithumenBaseUrl = this.configService.getOrThrow<string>(
      'tracker.bithumen-url',
    );
  }

  login(payload: BithumenLoginRequest) {
    return this.bithumenClientFactory.login(payload);
  }

  find(payload: BithumenTorrentsQuery) {
    return this.findAll(payload);
  }

  private async findAll(
    payload: BithumenTorrentsQuery,
    page: number = 0,
    accumulator: BithumenTorrent[] = [],
  ): Promise<BithumenTorrent[]> {
    try {
      const { imdbId, categories } = payload;

      const torrentsUrl = new URL(BITHUMEN_TORRENTS_PATH, this.bithumenBaseUrl);
      torrentsUrl.searchParams.append('genre', '0');
      torrentsUrl.searchParams.append('search', imdbId);
      torrentsUrl.searchParams.append('page', `${page}`);

      categories.forEach((category) => {
        torrentsUrl.searchParams.append(`c${category}`, '1');
      });

      const response = await this.bithumenClientFactory.client.get<string>(
        torrentsUrl.href,
        {
          responseType: 'text',
        },
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
      const detailsUrl = new URL(BITHUMEN_DETAILS_PATH, this.bithumenBaseUrl);
      detailsUrl.searchParams.append('id', torrentId);

      const response = await this.bithumenClientFactory.client.get<string>(
        detailsUrl.href,
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

      const downloadUrl = new URL(downloadPath, this.bithumenBaseUrl);

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

    const response = await this.bithumenClientFactory.client.get<ArrayBuffer>(
      downloadUrl,
      {
        responseType: 'arraybuffer',
      },
    );

    const bytes = new Uint8Array(response.data);
    const parsed = await parseTorrent(bytes);

    return { torrentId, parsed };
  }

  async hitnrun(): Promise<string[]> {
    try {
      const userId = await this.bithumenClientFactory.getUserId();

      const hitAndRunUrl = new URL(
        BITHUMEN_HIT_N_RUN_PATH,
        this.bithumenBaseUrl,
      );
      hitAndRunUrl.searchParams.append('id', userId);
      hitAndRunUrl.searchParams.append('hnr', '1');

      const response = await this.bithumenClientFactory.client.get<string>(
        hitAndRunUrl.href,
        {
          responseType: 'text',
        },
      );

      const $ = load(response.data);
      const hitnrunTorrents = $('td a[href*="/details.php?id="]');
      const torrentIds = hitnrunTorrents
        .map((_, el) => $(el).attr('href'))
        .get();

      const sourceIds = torrentIds.map((hitnrunTorrent) => {
        const url = new URL(hitnrunTorrent, this.bithumenBaseUrl);
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
        const downloadUrl = new URL(downloadPath, this.bithumenBaseUrl);

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
}
