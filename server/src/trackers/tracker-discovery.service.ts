import { Injectable } from '@nestjs/common';
import { differenceWith, keyBy } from 'lodash';

import { TorrentsCacheStore } from 'src/torrents-cache/core/torrents-cache.store';
import { TorrentCache } from 'src/torrents-cache/type/torrent-cache.type';

import { AdapterTorrent } from './adapters/adapters.types';
import { TrackersStore } from './core/trackers.store';
import { TrackerEnum } from './enum/tracker.enum';
import { TrackersMetaService } from './meta/trackers-meta.service';
import { TrackerAdapterRegistry } from './tracker-adapter.registry';
import {
  TrackerAdapter,
  TrackerSearchQuery,
  TrackerTorrent,
} from './tracker.types';
import { TrackerTorrentFound } from './type/tracker-torrent-found.type';

@Injectable()
export class TrackerDiscoveryService {
  constructor(
    private readonly trackersStore: TrackersStore,
    private readonly trackersMetaService: TrackersMetaService,
    private readonly trackerAdapterRegistry: TrackerAdapterRegistry,
    private readonly torrentsCacheStore: TorrentsCacheStore,
  ) {}

  async findTorrents(
    query: TrackerSearchQuery,
  ): Promise<PromiseSettledResult<TrackerTorrent[]>[]> {
    const trackers = await this.trackersStore.find();

    if (trackers.length === 0) {
      throw new Error(
        '[StremHU Source] Használat előtt konfigurálnod kell tracker bejelentkezést.',
      );
    }

    const results = await Promise.allSettled(
      trackers.map((tracker) => {
        const adapter = this.trackerAdapterRegistry.get(tracker.tracker);
        return this.findTrackerTorrents(adapter, query);
      }),
    );

    return results;
  }

  async findOne(
    torrentId: string,
  ): Promise<PromiseSettledResult<TrackerTorrentFound>[]> {
    const trackers = await this.trackersStore.find();

    if (trackers.length === 0) {
      throw new Error(
        '[StremHU Source] Használat előtt konfigurálnod kell tracker bejelentkezést.',
      );
    }

    const results = await Promise.allSettled(
      trackers.map((tracker) => {
        return this.findOneByTracker(tracker.tracker, torrentId);
      }),
    );

    return results;
  }

  async findOneByTracker(
    tracker: TrackerEnum,
    torrentId: string,
  ): Promise<TrackerTorrentFound> {
    const adapter = this.trackerAdapterRegistry.get(tracker);

    const torrentCache = await this.torrentsCacheStore.findOne({
      tracker,
      torrentId,
    });

    if (torrentCache) {
      return {
        tracker,
        torrentId: torrentCache.torrentId,
        infoHash: torrentCache.info.infoHash,
        torrentFilePath: torrentCache.torrentFilePath,
      };
    }

    const torrent = await adapter.findOne(torrentId);

    const downloaded = await adapter.download(torrent);
    const createdTorrentCache = await this.torrentsCacheStore.create({
      tracker,
      torrentId,
      torrentBuffer: downloaded.torrentBuffer,
    });

    return {
      tracker: createdTorrentCache.tracker,
      torrentId: createdTorrentCache.torrentId,
      infoHash: createdTorrentCache.info.infoHash,
      torrentFilePath: createdTorrentCache.torrentFilePath,
    };
  }

  private async findTrackerTorrents(
    adapter: TrackerAdapter,
    query: TrackerSearchQuery,
  ): Promise<TrackerTorrent[]> {
    const torrents = await adapter.find(query);
    const torrentsWithImdbId = torrents.filter((torrent) => torrent.imdbId);
    const torrentIds = torrentsWithImdbId.map(
      (torrentWithImdbId) => torrentWithImdbId.torrentId,
    );

    const existCachedTorrents = await this.torrentsCacheStore.findByTorrentId(
      adapter.tracker,
      torrentIds,
    );

    const notCachedTorrents = differenceWith(
      torrentsWithImdbId,
      existCachedTorrents,
      (torrent, cachedTorrent) => torrent.torrentId === cachedTorrent.torrentId,
    );
    const downloadedCachedTorrents = await this.downloads(
      adapter,
      notCachedTorrents,
      torrentsWithImdbId.length,
    );

    const cachedTorrents = [
      ...existCachedTorrents,
      ...downloadedCachedTorrents,
    ];

    const torrentsMap = keyBy(torrentsWithImdbId, 'torrentId');

    return cachedTorrents.map((cachedTorrent) => {
      const torrent = torrentsMap[cachedTorrent.torrentId];

      return {
        ...torrent,
        imdbId: torrent.imdbId!,
        infoHash: cachedTorrent.info.infoHash,
        name: cachedTorrent.info.name,
        files: cachedTorrent.info.files,
        torrentFilePath: cachedTorrent.torrentFilePath,
      };
    });
  }

  private async downloads(
    adapter: TrackerAdapter,
    adapterTorrents: AdapterTorrent[],
    torrentsCount: number,
  ): Promise<TorrentCache[]> {
    if (adapterTorrents.length === 0) {
      return [];
    }

    const results = await Promise.allSettled(
      adapterTorrents.map(async (adapterTorrent) => {
        const downloadedTorrent = await adapter.download(adapterTorrent);

        const createdTorrentCache = await this.torrentsCacheStore.create({
          torrentId: adapterTorrent.torrentId,
          tracker: adapterTorrent.tracker,
          torrentBuffer: downloadedTorrent.torrentBuffer,
        });

        return createdTorrentCache;
      }),
    );

    const failedFetches = results.filter(
      (result) => result.status === 'rejected',
    );

    if (failedFetches.length === torrentsCount) {
      throw new Error(
        `Nem sikerült torrentet letölteni a ${this.trackersMetaService.resolve(adapter.tracker).label}-ról.`,
      );
    }

    return results.flatMap((result) =>
      result.status === 'fulfilled' ? [result.value] : [],
    );
  }
}
