import { Injectable } from '@nestjs/common';
import _ from 'lodash';

import { TorrentsCacheStore } from 'src/torrents-cache/core/torrents-cache.store';

import {
  AdapterParsedTorrent,
  AdapterTorrentId,
} from './adapters/adapters.types';
import { TrackersStore } from './core/trackers.store';
import { TrackerTorrentStatusEnum } from './enum/tracker-torrent-status.enum';
import { TrackerEnum } from './enum/tracker.enum';
import { TrackerAdapterRegistry } from './tracker-adapter.registry';
import {
  TrackerAdapter,
  TrackerSearchQuery,
  TrackerTorrent,
  TrackerTorrentId,
} from './tracker.types';

@Injectable()
export class TrackerDiscoveryService {
  constructor(
    private readonly trackersStore: TrackersStore,
    private readonly trackerAdapterRegistry: TrackerAdapterRegistry,
    private readonly torrentsCacheStore: TorrentsCacheStore,
  ) {}

  async findTorrents(query: TrackerSearchQuery): Promise<TrackerTorrent[]> {
    const credentials = await this.trackersStore.find();

    if (credentials.length === 0) {
      return [
        {
          status: TrackerTorrentStatusEnum.ERROR,
          message:
            '[StremHU | Source] Használat előtt konfigurálnod kell tracker bejelentkezést.',
        },
      ];
    }

    const results = await Promise.all(
      credentials.map((credential) => {
        const adapter = this.trackerAdapterRegistry.get(credential.tracker);
        return this.findTrackerTorrents(adapter, query);
      }),
    );

    return results.flat();
  }

  async findOneTorrent(
    tracker: TrackerEnum,
    torrentId: string,
  ): Promise<TrackerTorrentId> {
    const adapter = this.trackerAdapterRegistry.get(tracker);

    const torrent = await adapter.findOne(torrentId);
    const torrentCache = await this.torrentsCacheStore.findOne(torrent);

    if (torrentCache) {
      return {
        ...torrent,
        parsed: torrentCache.parsed,
      };
    }

    const downloaded = await adapter.download(torrent);
    await this.torrentsCacheStore.create({
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

  private async findTrackerTorrents(
    adapter: TrackerAdapter,
    query: TrackerSearchQuery,
  ): Promise<TrackerTorrent[]> {
    try {
      const { imdbId } = query;

      const torrents = await adapter.find(query);
      const cachedTorrents = await this.torrentsCacheStore.find({
        imdbId,
        tracker: adapter.tracker,
      });

      const notCachedTorrents = _.differenceWith(
        torrents,
        cachedTorrents,
        (torrent, cachedTorrent) =>
          torrent.torrentId === cachedTorrent.torrentId,
      );
      const torrentParsedFiles = await this.downloads(
        adapter,
        notCachedTorrents,
      );

      const notAvailableTorrents = _.differenceWith(
        cachedTorrents,
        torrents,
        (cachedTorrent, torrent) =>
          torrent.torrentId === cachedTorrent.torrentId,
      );
      await this.torrentsCacheStore.delete(
        notAvailableTorrents.map(
          (notAvailableTorrent) => notAvailableTorrent.path,
        ),
      );

      const allTorrent = [...cachedTorrents, ...torrentParsedFiles];

      const allTorrentMap = _.keyBy(allTorrent, 'torrentId');

      return torrents.map((torrent) => {
        return {
          ...torrent,
          status: TrackerTorrentStatusEnum.SUCCESS,
          parsed: allTorrentMap[torrent.torrentId].parsed,
        };
      });
    } catch (error) {
      let message = 'Hiba történt';

      if (
        _.isObject(error) &&
        'message' in error &&
        typeof error.message === 'string'
      ) {
        message = error.message;
      }

      return [
        {
          status: TrackerTorrentStatusEnum.ERROR,
          message,
        },
      ];
    }
  }

  private async downloads(
    adapter: TrackerAdapter,
    adapterTorrents: AdapterTorrentId[],
  ): Promise<AdapterParsedTorrent[]> {
    const adapterParsedTorrents = await Promise.all(
      adapterTorrents.map(async (adapterTorrent) => {
        const adapterParsedTorrent = await adapter.download(adapterTorrent);

        await this.torrentsCacheStore.create({
          imdbId: adapterTorrent.imdbId,
          parsed: adapterParsedTorrent.parsed,
          torrentId: adapterTorrent.torrentId,
          tracker: adapterTorrent.tracker,
        });

        return adapterParsedTorrent;
      }),
    );

    return adapterParsedTorrents;
  }
}
