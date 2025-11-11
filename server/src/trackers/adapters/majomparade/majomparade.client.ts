import { Injectable, NotFoundException } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { load } from 'cheerio';
import _ from 'lodash';

import { parseTorrent } from 'src/common/utils/parse-torrent.util';
import { TrackerEnum } from 'src/trackers/enums/tracker.enum';

import { AdapterParsedTorrent, AdapterTorrentId } from '../adapters.types';
import { MajomparadeClientFactory } from './majomparade.client-factory';
import {
  MAJOMPARADE_DOWNLOAD_PATH,
  MAJOMPARADE_HIT_N_RUN_PATH,
  MAJOMPARADE_TORRENTS_PATH,
} from './majomparade.constants';
import {
  MajomparadeCategory,
  MajomparadeLoginRequest,
  MajomparadeTorrent,
  MajomparadeTorrents,
  MajomparadeTorrentsQuery,
} from './majomparade.types';

@Injectable()
export class MajomparadeClient {
  private readonly majomparadeBaseUrl: string;

  constructor(
    private configService: ConfigService,
    private majomparadeClientFactory: MajomparadeClientFactory,
  ) {
    this.majomparadeBaseUrl = this.configService.getOrThrow<string>(
      'tracker.bithumen-url',
    );
  }

  login(payload: MajomparadeLoginRequest) {
    return this.majomparadeClientFactory.login(payload, true);
  }

  find(payload: MajomparadeTorrentsQuery) {
    return this.findAll(payload);
  }

  private async findAll(
    payload: MajomparadeTorrentsQuery,
    page: number = 0,
    accumulator: MajomparadeTorrent[] = [],
  ): Promise<MajomparadeTorrent[]> {
    const { imdbId, categories } = payload;

    const url = new URL(MAJOMPARADE_TORRENTS_PATH, this.majomparadeBaseUrl);

    url.searchParams.append('tipus', '1');
    url.searchParams.append('tipuska', '0');
    url.searchParams.append('imdb_search', 'yes');
    url.searchParams.append('name', `https://www.imdb.com/title/${imdbId}/`);
    url.searchParams.append('page', `${page}`);

    // Ténylegesen az IMDB URL kell

    categories.forEach((category) => {
      url.searchParams.append(`category[]`, `${category}`);
    });

    const response = await this.majomparadeClientFactory.client.get<unknown>(
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
    const url = new URL(MAJOMPARADE_DOWNLOAD_PATH, this.majomparadeBaseUrl);
    url.searchParams.append('id', 'torrentId');

    const response = await this.majomparadeClientFactory.client.get<string>(
      url.toString(),
    );

    const $ = load(response.data);

    const downloadPath = $(`a[href*="download.php?torrent=${torrentId}"]`)
      .first()
      .attr('href');
    const imdbUrl =
      $('a[href*="www.imdb.com/title/"]').first().attr('href') || '';

    const imdbId = _.nth(imdbUrl.split('/'), -2);

    if (!downloadPath || !imdbId) {
      throw new NotFoundException(
        'majomparade torrent adatlapja nem található',
      );
    }

    const downloadUrl = new URL(
      downloadPath,
      this.majomparadeBaseUrl,
    ).toString();

    return {
      tracker: TrackerEnum.BITHUMEN,
      torrentId,
      imdbId,
      downloadUrl,
    };
  }

  async download(payload: AdapterTorrentId): Promise<AdapterParsedTorrent> {
    const { torrentId, downloadUrl } = payload;

    const response =
      await this.majomparadeClientFactory.client.get<ArrayBuffer>(downloadUrl, {
        responseType: 'arraybuffer',
      });

    const bytes = new Uint8Array(response.data);
    const parsed = await parseTorrent(bytes);

    return { torrentId, parsed };
  }

  /**
   * Visszaadja a “hit & run” nCore torrentek azonosítóit.
   */
  async hitnrun(): Promise<string[]> {
    const url = new URL(
      MAJOMPARADE_HIT_N_RUN_PATH,
      this.majomparadeBaseUrl,
    ).toString();

    const response =
      await this.majomparadeClientFactory.client.get<unknown>(url);

    if (typeof response.data !== 'string') {
      return [];
    }

    const $ = load(response.data);

    const hitnrunTorrents = $('td a[href*="/details.php?id="')
      .map((_, el) => $(el).attr('href'))
      .get();

    const sourceIds = hitnrunTorrents.map((hitnrunTorrent) => {
      const url = new URL(hitnrunTorrent, this.majomparadeBaseUrl);
      const idParam = url.searchParams.get('id');
      return idParam;
    });

    return _.compact(sourceIds);
  }

  private processTorrentsHtml(html: unknown): MajomparadeTorrents {
    if (typeof html !== 'string') {
      return {
        results: [],
        hasNextPage: false,
      };
    }

    const $ = load(html);
    const torrentRows = $('#table tbody tr').slice(1);

    const torrents: MajomparadeTorrent[] = [];

    torrentRows
      .each((_, torrentRow) => {
        const torrentColumns = $(torrentRow).children('td');

        // Kategória
        const CATEGORY_URL = 'letoltes.php?k=yes&tipus=1&category[]=';
        const categoryHref = torrentColumns
          .eq(0)
          .find(`a[href*="${CATEGORY_URL}"]`)
          .attr('href');
        if (!categoryHref) return;

        // Letöltés
        const downloadPath = torrentColumns
          .find(`a[href*="download.php?torrent="]`)
          .first()
          .attr('href');
        if (!downloadPath) return;

        // Torrent ID
        const torrentId = `${downloadPath}`.replace(
          'download.php?torrent=',
          '',
        );

        // Seeder
        const seeders = torrentColumns.eq(8).text();

        const categoryId = categoryHref.replace(CATEGORY_URL, '');
        const downloadUrl = new URL(
          downloadPath,
          this.majomparadeBaseUrl,
        ).toString();

        torrents.push({
          torrentId,
          downloadUrl,
          category: categoryId as MajomparadeCategory,
          seeders: seeders,
        });
      })
      .get();

    const nextLink = $('p b')
      .filter((_, el) => $(el).text().includes('Következő >>'))
      .first();

    const hasNextPage = nextLink.length > 0 && nextLink.parent().is('a');

    return {
      results: torrents,
      hasNextPage,
    };
  }
}
