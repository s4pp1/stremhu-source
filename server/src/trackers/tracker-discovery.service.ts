import { Injectable } from '@nestjs/common';
import { differenceWith, keyBy } from 'lodash';

import { TorrentsCacheStore } from 'src/torrents-cache/core/torrents-cache.store';
import { TorrentCache } from 'src/torrents-cache/torrents-cache.types';

import { AdapterTorrentId } from './adapters/adapters.types';
import { TrackersStore } from './core/trackers.store';
import { TrackerEnum } from './enum/tracker.enum';
import { TrackerAdapterRegistry } from './tracker-adapter.registry';
import {
  TrackerAdapter,
  TrackerSearchQuery,
  TrackerTorrent,
  TrackerTorrentFile,
} from './tracker.types';
import { TRACKER_INFO } from './trackers.constants';
import { TrackerTorrentFound } from './type/tracker-torrent-found.type';

@Injectable()
export class TrackerDiscoveryService {
  constructor(
    private readonly trackersStore: TrackersStore,
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

  async findOneTorrent(
    tracker: TrackerEnum,
    torrentId: string,
  ): Promise<TrackerTorrentFound> {
    const adapter = this.trackerAdapterRegistry.get(tracker);

    const torrent = await adapter.findOne(torrentId);
    const torrentCache = await this.torrentsCacheStore.findOne(torrent);

    if (torrentCache) {
      return {
        ...torrent,
        infoHash: torrentCache.parsed.infoHash,
        torrentFilePath: torrentCache.torrentFilePath,
      };
    }

    const downloaded = await adapter.download(torrent);
    const createdTorrentCache = await this.torrentsCacheStore.create({
      tracker,
      torrentId,
      imdbId: torrent.imdbId,
      parsed: downloaded.parsed,
    });

    return {
      ...torrent,
      infoHash: createdTorrentCache.parsed.infoHash,
      torrentFilePath: createdTorrentCache.torrentFilePath,
    };
  }

  private async findTrackerTorrents(
    adapter: TrackerAdapter,
    query: TrackerSearchQuery,
  ): Promise<TrackerTorrent[]> {
    const { imdbId } = query;

    const torrents = await adapter.find(query);
    const existCachedTorrents = await this.torrentsCacheStore.find({
      imdbId,
      tracker: adapter.tracker,
    });

    const notCachedTorrents = differenceWith(
      torrents,
      existCachedTorrents,
      (torrent, cachedTorrent) => torrent.torrentId === cachedTorrent.torrentId,
    );
    const downloadedCachedTorrents = await this.downloads(
      adapter,
      notCachedTorrents,
      torrents.length,
    );

    const cachedTorrents = [
      ...existCachedTorrents,
      ...downloadedCachedTorrents,
    ];

    const notAvailableTorrents = differenceWith(
      cachedTorrents,
      torrents,
      (cachedTorrent, torrent) => torrent.torrentId === cachedTorrent.torrentId,
    );
    await this.torrentsCacheStore.delete(
      notAvailableTorrents.map(
        (notAvailableTorrent) => notAvailableTorrent.torrentFilePath,
      ),
    );

    const torrentsMap = keyBy(torrents, 'torrentId');

    return cachedTorrents.map((cachedTorrent) => {
      const torrent = torrentsMap[cachedTorrent.torrentId];

      const name = cachedTorrent.parsed.name || '';

      const parsedFiles = cachedTorrent.parsed.files || [];
      const files: TrackerTorrentFile[] = parsedFiles.map(
        (parsedFile, index) => ({
          name: parsedFile.name,
          size: parsedFile.length,
          fileIndex: index,
        }),
      );

      return {
        ...torrent,
        infoHash: cachedTorrent.parsed.infoHash,
        name,
        files,
        torrentFilePath: cachedTorrent.torrentFilePath,
      };
    });
  }

  private async downloads(
    adapter: TrackerAdapter,
    adapterTorrents: AdapterTorrentId[],
    torrentsCount: number,
  ): Promise<TorrentCache[]> {
    if (adapterTorrents.length === 0) {
      return [];
    }

    const results = await Promise.allSettled(
      adapterTorrents.map(async (adapterTorrent) => {
        const adapterParsedTorrent = await adapter.download(adapterTorrent);

        const createdTorrentCache = await this.torrentsCacheStore.create({
          imdbId: adapterTorrent.imdbId,
          parsed: adapterParsedTorrent.parsed,
          torrentId: adapterTorrent.torrentId,
          tracker: adapterTorrent.tracker,
        });

        return createdTorrentCache;
      }),
    );

    const failedFetches = results.filter(
      (result) => result.status === 'rejected',
    );

    if (failedFetches.length === torrentsCount) {
      throw new Error(
        `Nem sikerült torrentet letölteni a ${TRACKER_INFO[adapter.tracker].label}-ról.`,
      );
    }

    return results.flatMap((result) =>
      result.status === 'fulfilled' ? [result.value] : [],
    );
  }
}
