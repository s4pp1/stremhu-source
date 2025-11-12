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
import { NcoreClientFactory } from './ncore.client-factory';
import { NCORE_HIT_N_RUN_PATH, NCORE_TORRENTS_PATH } from './ncore.constants';
import {
  NcoreDownloadRequest,
  NcoreFindQuery,
  NcoreLoginRequest,
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
  private readonly ncoreBaseUrl: string;

  constructor(
    @Inject(TRACKER_TOKEN) private readonly tracker: TrackerEnum,
    private configService: ConfigService,
    private ncoreClientFactory: NcoreClientFactory,
  ) {
    this.ncoreBaseUrl =
      this.configService.getOrThrow<string>('tracker.ncore-url');
  }

  login(payload: NcoreLoginRequest) {
    return this.ncoreClientFactory.login(payload);
  }

  async find(payload: NcoreFindQuery): Promise<NcoreTorrent[]> {
    return this.findAll(payload);
  }

  private async findAll(
    payload: NcoreFindQuery,
    page: number = 1,
    accumulator: NcoreTorrent[] = [],
  ): Promise<NcoreTorrent[]> {
    const { imdbId, categories } = payload;

    const torrentsUrl = new URL(NCORE_TORRENTS_PATH, this.ncoreBaseUrl);

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

    const response = await this.ncoreClientFactory.client.get<NcoreTorrents>(
      torrentsUrl.href,
      {
        params: searchParams,
      },
    );

    accumulator = [...accumulator, ...response.data.results];

    const total = Number(response.data.total_results);
    const limit = Number(response.data.perpage);
    const lastPage = Math.ceil(total / limit);

    if (lastPage > page) {
      return this.findAll(payload, page + 1, accumulator);
    }

    return accumulator;
  }

  async findOne(torrentId: string): Promise<AdapterTorrentId> {
    try {
      const detailsUrl = new URL(NCORE_TORRENTS_PATH, this.ncoreBaseUrl);

      detailsUrl.searchParams.append('action', 'details');
      detailsUrl.searchParams.append('id', torrentId);

      const response = await this.ncoreClientFactory.client.get<string>(
        detailsUrl.href,
      );

      const $ = load(response.data);

      const downloadPath = $(
        `.download a[href*="torrents.php?action=download&id=${torrentId}"]`,
      )
        .first()
        .attr('href');

      const imdbUrl = $(
        'a[href*=https://dereferer.me/?https://imdb.com/title/]',
      )
        .first()
        .text();

      const imdbId = _.last(imdbUrl.split('/'));

      if (!downloadPath || !imdbId) {
        throw new Error(
          `"downloadPath": ${downloadPath} vagy "imdbId": ${imdbId} nem található`,
        );
      }

      const downloadUrl = new URL(downloadPath, this.ncoreBaseUrl);

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

  async download(payload: NcoreDownloadRequest): Promise<AdapterParsedTorrent> {
    const { torrentId, downloadUrl } = payload;

    const response = await this.ncoreClientFactory.client.get<ArrayBuffer>(
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
      const hitAndRunUrl = new URL(NCORE_HIT_N_RUN_PATH, this.ncoreBaseUrl);
      hitAndRunUrl.searchParams.append('showall', 'false');

      const response = await this.ncoreClientFactory.client.get<string>(
        hitAndRunUrl.href,
        {
          responseType: 'text',
        },
      );

      const $ = load(response.data);

      const hitnrunTorrents = $(
        '.box_torrent_all a[href*="torrents.php?action=details&id="',
      )
        .map((_, el) => $(el).attr('href'))
        .get();

      const sourceIds = hitnrunTorrents.map((hitnrunTorrent) => {
        const url = new URL(hitnrunTorrent, this.ncoreBaseUrl);
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
}
