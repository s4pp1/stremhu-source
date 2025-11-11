import { Inject, Injectable, NotFoundException } from '@nestjs/common';
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
import { BithumenClientFactory } from './bithumen.client-factory';
import {
  BITHUMEN_DOWNLOAD_PATH,
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
    return this.bithumenClientFactory.login(payload, true);
  }

  find(payload: BithumenTorrentsQuery) {
    return this.findAll(payload);
  }

  private async findAll(
    payload: BithumenTorrentsQuery,
    page: number = 0,
    accumulator: BithumenTorrent[] = [],
  ): Promise<BithumenTorrent[]> {
    const { imdbId, categories } = payload;

    const url = new URL(BITHUMEN_TORRENTS_PATH, this.bithumenBaseUrl);
    url.searchParams.append('genre', '0');
    url.searchParams.append('search', imdbId);
    url.searchParams.append('page', `${page}`);

    categories.forEach((category) => {
      url.searchParams.append(`c${category}`, '1');
    });

    const response = await this.bithumenClientFactory.client.get<unknown>(
      url.toString(),
    );

    const data = this.processTorrentsHtml(response.data);

    accumulator = [...accumulator, ...data.results];

    if (data.hasNextPage) {
      return this.findAll(payload, page + 1, accumulator);
    } else {
      return accumulator;
    }
  }

  async findOne(torrentId: string): Promise<AdapterTorrentId> {
    const url = new URL(
      BITHUMEN_DOWNLOAD_PATH.replace(
        '{TORRENT_ID}',
        encodeURIComponent(torrentId),
      ),
      this.bithumenBaseUrl,
    ).toString();

    const response = await this.bithumenClientFactory.client.get<string>(url);

    const $ = load(response.data);

    const downloadPath = $(`a[href*="download.php/${torrentId}"]`)
      .first()
      .attr('href');
    const imdbUrl =
      $('a[href*="www.imdb.com/title/"]').first().attr('href') || '';

    const imdbId = _.nth(imdbUrl.split('/'), -2);

    if (!downloadPath || !imdbId) {
      throw new NotFoundException('bitHUmen torrent adatlapja nem található');
    }

    const downloadUrl = new URL(downloadPath, this.bithumenBaseUrl).toString();

    return {
      tracker: this.tracker,
      torrentId,
      imdbId,
      downloadUrl,
    };
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

  /**
   * Visszaadja a “hit & run” nCore torrentek azonosítóit.
   */
  async hitnrun(): Promise<string[]> {
    const url = new URL(
      BITHUMEN_HIT_N_RUN_PATH.replace(
        '{USER_ID}',
        this.bithumenClientFactory.userId,
      ),
      this.bithumenBaseUrl,
    ).toString();

    const response = await this.bithumenClientFactory.client.get<unknown>(url);

    if (typeof response.data !== 'string') {
      return [];
    }

    const $ = load(response.data);

    const hitnrunTorrents = $('td a[href*="/details.php?id="')
      .map((_, el) => $(el).attr('href'))
      .get();

    const sourceIds = hitnrunTorrents.map((hitnrunTorrent) => {
      const url = new URL(hitnrunTorrent, this.bithumenBaseUrl);
      const idParam = url.searchParams.get('id');
      return idParam;
    });

    return _.compact(sourceIds);
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

        // Kategória
        const categoryHref = torrentColumns.eq(0).find('a').attr('href') || '';
        const category = categoryHref.replace('?cat=', '');

        // Letöltés
        const downloadPath = torrentColumns
          .eq(1)
          .children('a')
          .eq(1)
          .attr('href')!;
        const downloadUrl = new URL(
          downloadPath,
          this.bithumenBaseUrl,
        ).toString();

        // Torrent ID
        const torrentId = torrentColumns
          .eq(1)
          .children('a')
          .eq(0)
          .attr('href')!
          .replace('details.php?id=', '');

        // Seeder
        const seeders = torrentColumns.eq(7).text();

        return {
          torrentId,
          downloadUrl,
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
