import { Inject, Injectable, Logger } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import Bottleneck from 'bottleneck';
import { load } from 'cheerio';

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
import { FilelistClientFactory } from './filelist.client-factory';
import {
  DETAILS_PATH,
  HIT_N_RUN_PATH,
  TORRENTS_PATH,
} from './filelist.constants';
import {
  FilelistCategory,
  FilelistSearchInByEnum,
  FilelistSortByEnum,
  FilelistTorrent,
  FilelistTorrents,
  FilelistTorrentsQuery,
} from './filelist.types';

@Injectable()
export class FilelistClient {
  private readonly logger = new Logger(FilelistClient.name);
  private readonly limiter: Bottleneck;
  private readonly baseUrl: string;

  constructor(
    @Inject(TRACKER_TOKEN) private readonly tracker: TrackerEnum,
    private configService: ConfigService,
    private filelistClientFactory: FilelistClientFactory,
  ) {
    this.baseUrl = this.configService.getOrThrow<string>(
      'tracker.filelist-url',
    );

    const maxConcurrent = this.configService.getOrThrow<number>(
      'tracker.filelist-max-concurrent',
    );

    this.limiter = new Bottleneck({ maxConcurrent });
  }

  login(payload: AdapterLoginRequest): Promise<void> {
    return this.requestLimit(() => this.filelistClientFactory.login(payload));
  }

  find(payload: FilelistTorrentsQuery): Promise<FilelistTorrent[]> {
    return this.findWithResolvedSearchParams(payload);
  }

  private async findWithResolvedSearchParams(
    payload: FilelistTorrentsQuery,
  ): Promise<FilelistTorrent[]> {
    const {
      searchTerm,
      searchIn,
    } = payload.series != null ? {
      searchTerm: `s${payload.series.season.toString().padStart(2, '0')} ${payload.imdbId.replace('tt', '')}`,
      searchIn: FilelistSearchInByEnum.NAME_DESCRIPTION,
    } : {
        searchTerm: payload.imdbId,
        searchIn: FilelistSearchInByEnum.IMDB,
      };

    const imdbResults = await this.findAll(
      payload,
      searchTerm,
      searchIn,
    );

    return imdbResults;
  }

  private async findAll(
    payload: FilelistTorrentsQuery,
    searchTerm: string,
    searchIn: FilelistSearchInByEnum,
    page: number = 0,
    accumulator: FilelistTorrent[] = [],
  ): Promise<FilelistTorrent[]> {
    this.logger.log(`[${this.tracker}] Searching for torrents: ${searchTerm} in ${searchIn} on page ${page}`);

    if (accumulator.length > FIND_TORRENTS_LIMIT) {
      return accumulator;
    }

    try {
      const { imdbId, categories } = payload;
      const torrentsUrl = new URL(TORRENTS_PATH, this.baseUrl);

      torrentsUrl.searchParams.append('search', searchTerm);
      torrentsUrl.searchParams.append('searchin', searchIn.toString());
      torrentsUrl.searchParams.append('sort', FilelistSortByEnum.PEERS.toString());
      torrentsUrl.searchParams.append('incldead', '0');
      torrentsUrl.searchParams.append('page', `${page}`);

      categories.forEach((category, index) => {
        // torrentsUrl.searchParams.append(`cats[${index}]`, category);
        torrentsUrl.searchParams.append(`cats[${index}]`, category);
      });

      const response = await this.requestLimit(() =>
        this.filelistClientFactory.client.get<string>(torrentsUrl.href, {
          responseType: 'text',
        }),
      );

      const data = this.processTorrentsHtml(response.data);
      const results = data.results
        .filter((torrent) => categories.includes(torrent.category))
        .map((torrent) => ({
          ...torrent,
          imdbId: torrent.imdbId || imdbId,
        }));
      accumulator = [...accumulator, ...results];

      if (data.hasNextPage) {
        return this.findAll(payload, searchTerm, searchIn, page + 1, accumulator);
      }

      return accumulator.filter((torrent) => torrent.imdbId === imdbId);
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
        this.filelistClientFactory.client.get<string>(detailsUrl.href, {
          responseType: 'text',
        }),
      );

      const $ = load(response.data);
      const downloadPath = $(`a[href*="download.php?id=${torrentId}"]`)
        .first()
        .attr('href');
      const imdbUrl =
        $('a[href*="www.imdb.com/title/"], a[href*="imdb.com/title/"]')
          .first()
          .attr('href') || '';
      const imdbId = this.resolveImdbId(imdbUrl);

      if (!downloadPath) {
        throw new Error(`A "downloadPath" nem talalhato!`);
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
        this.filelistClientFactory.client.get<ArrayBuffer>(downloadUrl, {
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
    try {
      const hitAndRunUrl = new URL(HIT_N_RUN_PATH, this.baseUrl);

      const response = await this.requestLimit(() =>
        this.filelistClientFactory.client.get<string>(hitAndRunUrl.href, {
          responseType: 'text',
        }),
      );

      return this.processHitAndRunHtml(response.data);
    } catch (error) {
      const errorMessage = getTrackerStructureErrorMessage(this.tracker);
      this.logger.error(errorMessage, error);
      throw new Error(errorMessage, { cause: error });
    }
  }

  private processTorrentsHtml(html: unknown): FilelistTorrents {
    if (typeof html !== 'string') {
      return { results: [], hasNextPage: false };
    }

    const $ = load(html);
    const torrentRows = $('.torrentrow');
    const torrents: FilelistTorrent[] = torrentRows
      .map((_, torrentRow) => {
        const torrentColumns = $(torrentRow).children('td, .torrenttable');

        const categoryHref =
          $(torrentRow)
            .find('a[href^="browse.php?cat="], a[href^="/browse.php?cat="]')
            .first()
            .attr('href') ||
          '';
        const categoryUrl = new URL(categoryHref, this.baseUrl);
        const category = categoryUrl.searchParams.get('cat') || '';

        const detailsPath =
          $(torrentRow)
            .find('a[href^="details.php?id="], a[href^="/details.php?id="]')
            .first()
            .attr('href') || '';
        const name =
          $(torrentRow)
            .find('a[href^="details.php?id="], a[href^="/details.php?id="]')
            .first()
            .attr('title') ||
          $(torrentRow)
            .find('a[href^="details.php?id="], a[href^="/details.php?id="]')
            .first()
            .text()
            .trim();
        const detailsUrl = new URL(detailsPath, this.baseUrl);
        const torrentId = detailsUrl.searchParams.get('id') || '';

        const downloadPath =
          $(torrentRow)
            .find('a[href^="download.php?id="], a[href^="/download.php?id="]')
            .first()
            .attr('href') || '';
        const downloadUrl = downloadPath
          ? new URL(downloadPath, this.baseUrl).href
          : '';

        const imdbUrl =
          torrentColumns
            .find('a[href*="www.imdb.com/title/"], a[href*="imdb.com/title/"]')
            .first()
            .attr('href') || '';
        const imdbId = this.resolveImdbId(imdbUrl) || '';

        const seeders = torrentColumns.eq(8).text().trim();

        return {
          name,
          torrentId,
          downloadUrl,
          category: category as FilelistCategory,
          seeders,
          imdbId,
        };
      })
      .get()
      .filter((torrent) => torrent.torrentId && torrent.downloadUrl);

    const hasNextPage =
      $('a').filter((_, el) => $(el).text().trim().includes('Next')).length >
      0;

    return { results: torrents, hasNextPage };
  }

  private processHitAndRunHtml(html: unknown): string[] {
    if (typeof html !== 'string') {
      throw new Error('A Filelist SnatchList nem talalhato.');
    }

    const $ = load(html);
    const pageText = this.normalizeHitAndRunStatusText($('body').text());
    const hasSnatchListMarker =
      pageText.includes('snatchlist') ||
      pageText.includes('snatch list') ||
      $('a[href*="snatchlist.php"], form[action*="snatchlist.php"]').length >
      0;

    if (!hasSnatchListMarker) {
      throw new Error('A Filelist SnatchList nem talalhato.');
    }

    const rows = $('tr').filter(
      (_, row) => $(row).find('a[href*="details.php?id="]').length > 0,
    );

    if (!rows.length) {
      if (this.hasEmptyHitAndRunState(pageText)) {
        return [];
      }

      throw new Error('A Filelist SnatchList torrent sorai nem talalhatok.');
    }

    const hitAndRunTorrentIds = new Set<string>();
    const unknownStatusTorrentIds: string[] = [];

    rows.each((_, row) => {
      const detailsPath = $(row)
        .find('a[href*="details.php?id="]')
        .first()
        .attr('href');
      const torrentId = this.resolveTorrentId(detailsPath || '');

      if (!torrentId) {
        return;
      }

      const rowWithoutTorrentLinks = $(row).clone();
      rowWithoutTorrentLinks.find('a[href*="details.php?id="]').remove();
      const statusParts = [
        rowWithoutTorrentLinks.text(),
        ...$(row)
          .find('[title], [alt], [aria-label], [class]')
          .filter(
            (_, element) =>
              !$(element).is('a[href*="details.php?id="]') &&
              $(element).parents('a[href*="details.php?id="]').length === 0,
          )
          .map((_, element) =>
            [
              $(element).attr('title') || '',
              $(element).attr('alt') || '',
              $(element).attr('aria-label') || '',
              $(element).attr('class') || '',
            ].join(' '),
          )
          .get(),
      ];
      const statusText = this.normalizeHitAndRunStatusText(
        statusParts.join(' '),
      );

      if (this.isHitAndRunStatus(statusText)) {
        hitAndRunTorrentIds.add(torrentId);
        return;
      }

      if (this.isCompletedSeedRequirementStatus(statusText)) {
        return;
      }

      unknownStatusTorrentIds.push(torrentId);
    });

    if (unknownStatusTorrentIds.length) {
      throw new Error(
        `A Filelist SnatchList statusza nem felismerheto: ${unknownStatusTorrentIds.join(
          ', ',
        )}.`,
      );
    }

    return [...hitAndRunTorrentIds];
  }

  private hasEmptyHitAndRunState(pageText: string): boolean {
    return [
      /\bno\s+(?:torrents|results|snatches|records)\s*(?:found|available)?\b/,
      /\bnothing\s+found\b/,
      /\bempty\b/,
      /\bnu\s+(?:exista|sunt)\s+(?:torrente|rezultate|inregistrari)\b/,
    ].some((pattern) => pattern.test(pageText));
  }

  private isHitAndRunStatus(statusText: string): boolean {
    return [
      /\bhnr\b/,
      /h\s*&\s*r/,
      /hit\s*(?:and|&)\s*run/,
      /needs?\s+(?:seed|seeding|ratio|time)/,
      /(?:seed|seeding|ratio|time)\s+(?:needed|required|missing|left)/,
      /not\s+(?:completed|cleared|ok|seeded|satisfied|fulfilled)/,
      /\b(?:incomplete|unsatisfied|unfulfilled|warning|danger|pending)\b/,
      /\b(?:nefinalizat|neterminat|nesatisfacut|neindeplinit|avertizare|risc|restant)\b/,
      /(?:necesita|trebuie).*(?:seed|ratio|ratie|timp)/,
    ].some((pattern) => pattern.test(statusText));
  }

  private isCompletedSeedRequirementStatus(statusText: string): boolean {
    return [
      /\b(?:complete|completed|cleared|ok|safe|done|satisfied|fulfilled)\b/,
      /\b(?:finalizat|completat|indeplinit|satisfacut)\b/,
      /\bseeded\b/,
    ].some((pattern) => pattern.test(statusText));
  }

  private normalizeHitAndRunStatusText(statusText: string): string {
    return statusText
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .toLowerCase()
      .replace(/[_-]+/g, ' ')
      .replace(/\s+/g, ' ')
      .trim();
  }

  private resolveTorrentId(detailsPath: string): string | undefined {
    try {
      const detailsUrl = new URL(detailsPath, this.baseUrl);
      return detailsUrl.searchParams.get('id') || undefined;
    } catch {
      return undefined;
    }
  }

  private resolveImdbId(imdbUrl: string): string | undefined {
    return imdbUrl.match(/\/title\/(tt\d+)/)?.[1];
  }

  private requestLimit<T>(fn: () => Promise<T>): Promise<T> {
    return this.limiter.schedule(fn);
  }
}
