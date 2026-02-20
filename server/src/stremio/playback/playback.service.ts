import { Injectable } from '@nestjs/common';

import { TorrentsCacheStore } from 'src/torrents-cache/core/torrents-cache.store';
import { TorrentsService } from 'src/torrents/torrents.service';
import { Torrent } from 'src/torrents/type/torrent.type';
import { TrackerDiscoveryService } from 'src/trackers/tracker-discovery.service';

import { PreparePlay } from './type/prepare-play.type';

@Injectable()
export class PlaybackService {
  private inFlightPlay = new Map<string, Promise<Torrent>>();

  constructor(
    private readonly torrentsCacheStore: TorrentsCacheStore,
    private readonly torrentsService: TorrentsService,
    private readonly trackerDiscoveryService: TrackerDiscoveryService,
  ) {}

  async preparePlayback(payload: PreparePlay): Promise<Torrent> {
    const { imdbId, tracker, torrentId } = payload;

    const key = `${imdbId}-${tracker}-${torrentId}`;
    const running = this.inFlightPlay.get(key);
    if (running) return running;

    const promise = this.getTorrent(payload);

    this.inFlightPlay.set(key, promise);

    try {
      const response = await promise;
      return response;
    } finally {
      this.inFlightPlay.delete(key);
    }
  }

  private async getTorrent(payload: PreparePlay): Promise<Torrent> {
    const { imdbId, tracker, torrentId } = payload;

    const torrentCache = await this.torrentsCacheStore.findOne({
      imdbId,
      tracker,
      torrentId,
    });

    let torrentFilePath: string | undefined;

    if (torrentCache) {
      torrentFilePath = torrentCache.torrentFilePath;
      const torrent = await this.torrentsService.findOneByInfoHash(
        torrentCache.info.infoHash,
      );

      if (torrent) return torrent;
    }

    if (!torrentFilePath) {
      const torrentFile = await this.trackerDiscoveryService.findOneTorrent(
        tracker,
        torrentId,
      );

      torrentFilePath = torrentFile.torrentFilePath;
    }

    let torrent = await this.torrentsService.addTorrent({
      imdbId,
      torrentId,
      tracker,
      torrentFilePath,
    });

    torrent = await this.torrentsService.updateOne(torrent.infoHash, {
      lastPlayedAt: new Date(),
    });

    return torrent;
  }
}
