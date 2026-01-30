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
import { InsaneClientFactory } from './insane.client-factory';
import {
  HIT_N_RUN_PATH,
  TORRENTS_PATH,
  TORRENT_DETAILS_PATH,
} from './insane.constants';
import { CategoryEnum, Torrent, Torrents, TorrentsQuery } from './insane.types';

@Injectable()
export class InsaneClient {
  private readonly logger = new Logger(InsaneClient.name);
  private readonly limiter: Bottleneck;

  private readonly baseUrl: string;

  constructor(
    @Inject(TRACKER_TOKEN) readonly tracker: TrackerEnum,
    private configService: ConfigService,
    private clientFactory: InsaneClientFactory,
  ) {
    this.baseUrl = this.configService.getOrThrow<string>('tracker.insane-url');

    const maxConcurrent = this.configService.getOrThrow<number>(
      'tracker.insane-max-concurrent',
    );

    this.limiter = new Bottleneck({
      maxConcurrent,
    });
  }

  login(payload: AdapterLoginRequest) {
    return this.requestLimit(() => this.clientFactory.login(payload));
  }

  find(payload: TorrentsQuery) {
    return this.findAll(payload);
  }

  private async findAll(
    payload: TorrentsQuery,
    page: number = 0,
    accumulator: Torrent[] = [],
  ): Promise<Torrent[]> {
    if (accumulator.length > FIND_TORRENTS_LIMIT) {
      return accumulator;
    }

    try {
      const { imdbId, categories } = payload;

      const torrentsUrl = new URL(TORRENTS_PATH, this.baseUrl);

      categories.forEach((category) => {
        torrentsUrl.searchParams.append(`cat[]`, category);
      });

      torrentsUrl.searchParams.append('search', imdbId);
      torrentsUrl.searchParams.append('page', `${page}`);

      torrentsUrl.searchParams.append('torart', 'tor');
      torrentsUrl.searchParams.append('incldead', '1');

      torrentsUrl.searchParams.append('sort', '7');
      torrentsUrl.searchParams.append('type', 'desc');

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

      return accumulator.filter((acc) => acc.imdbId === imdbId);
    } catch (error) {
      const errorMessage = getTrackerStructureErrorMessage(this.tracker);
      this.logger.error(errorMessage, error);
      throw new ServiceUnavailableException(errorMessage);
    }
  }

  async findOne(torrentId: string): Promise<AdapterTorrentId> {
    try {
      const detailsUrl = new URL(TORRENT_DETAILS_PATH, this.baseUrl);
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

      const response = await this.requestLimit(() =>
        this.clientFactory.client.get<string>(hitAndRunUrl.href, {
          responseType: 'text',
        }),
      );

      const $ = load(response.data);
      const hitnrunTorrents = $('td a[href*="details.php?id="]');
      const torrentIds = hitnrunTorrents
        .map((_, el) => $(el).attr('href'))
        .get();

      const sourceIds = torrentIds.map((hitnrunTorrent) => {
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

  private processTorrentsHtml(html: unknown): Torrents {
    if (typeof html !== 'string') {
      return {
        results: [],
        hasNextPage: false,
      };
    }

    const $ = load(html);
    const torrentRows = $('.torrenttable tbody .torrentrow');
    const torrents: Torrent[] = torrentRows
      .map((_, torrentRow) => {
        // Kategória feloldása
        const categoryHref =
          $(torrentRow)
            .find('a[href*="browse.php?cat="]')
            .first()
            .attr('href') || '';
        const category = categoryHref.replace('browse.php?cat=', '');

        // Torrent ID feloldása
        const torrentIdHref =
          $(torrentRow)
            .find('.torrentmain a[href*="details.php?id="]')
            .first()
            .attr('href') || '';
        const torrentId = torrentIdHref.replace('details.php?id=', '');

        // Letöltéshez szükséges URL
        const downloadUrl =
          $(torrentRow)
            .find(
              `.downloadlink a[href*="https://newinsane.info/download.php/${torrentId}/"]`,
            )
            .first()
            .attr('href') || '';

        // IMDB ID feloldása
        const imdbUrl =
          $(torrentRow)
            .find('a[href*="www.imdb.com/title/"]')
            .first()
            .attr('href') || '';
        const imdbId = nth(imdbUrl.split('/'), -2) || '';

        // Seeders feloldása
        const seeders = $(torrentRow).find('.data .leftborder').first().text();

        return {
          torrentId,
          downloadUrl: downloadUrl,
          category: category as CategoryEnum,
          seeders: seeders,
          imdbId: imdbId,
        };
      })
      .get();

    const hasNextPage = $('.top.pager.center a.pagernextlink').length > 0;

    return {
      results: torrents,
      hasNextPage,
    };
  }

  private requestLimit<T>(fn: () => Promise<T>) {
    return this.limiter.schedule(fn);
  }
}
