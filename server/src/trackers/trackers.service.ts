import {
  BadRequestException,
  Injectable,
  OnApplicationBootstrap,
} from '@nestjs/common';
import { Cron, CronExpression, SchedulerRegistry } from '@nestjs/schedule';
import _ from 'lodash';

import { SettingsStore } from 'src/settings/core/settings.store';
import { TorrentCacheStore } from 'src/torrent-cache/core/torrent-cache.store';
import { WebTorrentService } from 'src/web-torrent/web-torrent.service';

import {
  AdapterParsedTorrent,
  AdapterTorrentId,
} from './adapters/adapters.types';
import { BithumenAdapter } from './adapters/bithumen/bithumen.adapter';
import { NcoreAdapter } from './adapters/ncore/ncore.adapter';
import { TrackerCredentialsService } from './credentials/tracker-credentials.service';
import { TrackerEnum } from './enums/tracker.enum';
import {
  LoginRequest,
  TrackerAdapter,
  TrackerSearchQuery,
  TrackerTorrent,
  TrackerTorrentId,
} from './tracker.types';

@Injectable()
export class TrackersService implements OnApplicationBootstrap {
  private readonly adapters: TrackerAdapter[];

  constructor(
    ncoreAdapter: NcoreAdapter,
    bithumenAdapter: BithumenAdapter,
    private readonly schedulerRegistry: SchedulerRegistry,
    private trackerCredentialsService: TrackerCredentialsService,
    private torrentCacheStore: TorrentCacheStore,
    private webTorrentService: WebTorrentService,
    private settingsStore: SettingsStore,
  ) {
    this.adapters = [ncoreAdapter, bithumenAdapter];
  }

  async onApplicationBootstrap() {
    const setting = await this.settingsStore.findOneOrThrow();
    const job = this.schedulerRegistry.getCronJob('cleanupTorrents');

    if (!setting.hitAndRun) {
      await job.stop();
    }
  }

  async login(tracker: TrackerEnum, payload: LoginRequest): Promise<void> {
    const adapter = this.getAdapter(tracker);

    await adapter.login(payload);
    await this.trackerCredentialsService.create({
      tracker,
      ...payload,
    });
  }

  async findTorrents(query: TrackerSearchQuery): Promise<TrackerTorrent[]> {
    const results = await Promise.all(
      // this.adapters.map((adapter) => this.findTrackerTorrents(adapter, query)),
      [this.findTrackerTorrents(this.adapters[1], query)],
    );

    return results.flat();
  }

  async findOneTorrent(
    tracker: TrackerEnum,
    torrentId: string,
  ): Promise<TrackerTorrentId> {
    const adapter = this.getAdapter(tracker);

    const torrent = await adapter.findOne(torrentId);
    const torrentCache = await this.torrentCacheStore.findOne(torrent);

    if (torrentCache) {
      return {
        ...torrent,
        parsed: torrentCache.parsed,
      };
    }

    const downloaded = await adapter.download(torrent);
    await this.torrentCacheStore.create({
      tracker,
      torrentId,
      imdbId: torrent.imdbId,
      parsed: downloaded.parsed,
    });

    return {
      ...torrent,
      parsed: downloaded.parsed,
    };
  }

  async setHitAndRunCron(enabled: boolean) {
    const job = this.schedulerRegistry.getCronJob('cleanupTorrents');

    if (enabled && !job.isActive) {
      job.start();
    }

    if (!enabled && job.isActive) {
      await job.stop();
    }
  }

  @Cron(CronExpression.EVERY_DAY_AT_4AM, { name: 'cleanupTorrents' })
  async cleanupHitAndRun() {
    await Promise.all(
      this.adapters.map((adapter) => this.cleanupHitAndRunTracker(adapter)),
    );
  }

  private async cleanupHitAndRunTracker(adapter: TrackerAdapter) {
    const seedReqTorrentIds = await adapter.seedRequirement();
    await this.webTorrentService.purgeTrackerExcept(
      adapter.tracker,
      seedReqTorrentIds,
    );
  }

  private getAdapter(tracker: TrackerEnum): TrackerAdapter {
    const adapter = this.adapters.find((a) => a.tracker === tracker);
    if (!adapter) {
      throw new BadRequestException(`Nem regisztrált tracker: ${tracker}`);
    }
    return adapter;
  }

  private async findTrackerTorrents(
    adapter: TrackerAdapter,
    query: TrackerSearchQuery,
  ): Promise<TrackerTorrent[]> {
    const { imdbId } = query;

    const torrents = await adapter.find(query);
    const cachedTorrents = await this.torrentCacheStore.find({
      imdbId,
      tracker: adapter.tracker,
    });

    const notCachedTorrents = _.differenceWith(
      torrents,
      cachedTorrents,
      (torrent, cachedTorrent) => torrent.torrentId === cachedTorrent.torrentId,
    );
    const torrentParsedFiles = await this.downloads(adapter, notCachedTorrents);

    const notAvailableTorrents = _.differenceWith(
      cachedTorrents,
      torrents,
      (cachedTorrent, torrent) => torrent.torrentId === cachedTorrent.torrentId,
    );
    await this.torrentCacheStore.delete(
      notAvailableTorrents.map(
        (notAvailableTorrent) => notAvailableTorrent.path,
      ),
    );

    const allTorrent = [...cachedTorrents, ...torrentParsedFiles];

    const allTorrentMap = _.keyBy(allTorrent, 'torrentId');

    return torrents.map((torrent) => {
      return {
        ...torrent,
        parsed: allTorrentMap[torrent.torrentId].parsed,
      };
    });
  }

  private async downloads(
    adapter: TrackerAdapter,
    adapterTorrents: AdapterTorrentId[],
  ): Promise<AdapterParsedTorrent[]> {
    const adapterParsedTorrents: AdapterParsedTorrent[] = [];

    for (const adapterTorrent of adapterTorrents) {
      const adapterParsedTorrent = await adapter.download(adapterTorrent);
      adapterParsedTorrents.push(adapterParsedTorrent);

      await this.torrentCacheStore.create({
        imdbId: adapterTorrent.imdbId,
        parsed: adapterParsedTorrent.parsed,
        torrentId: adapterTorrent.torrentId,
        tracker: adapterTorrent.tracker,
      });
    }

    return adapterParsedTorrents;
  }
}
