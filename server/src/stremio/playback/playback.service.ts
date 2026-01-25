import { Injectable } from '@nestjs/common';

import { RelayTorrent } from 'src/relay/client';
import { TorrentsCacheStore } from 'src/torrents-cache/core/torrents-cache.store';
import { TorrentsService } from 'src/torrents/torrents.service';
import { TrackerDiscoveryService } from 'src/trackers/tracker-discovery.service';

import { PreparePlay } from './type/prepare-play.type';

@Injectable()
export class PlaybackService {
  private inFlightPlay = new Map<string, Promise<RelayTorrent>>();

  constructor(
    private readonly torrentsCacheStore: TorrentsCacheStore,
    private readonly torrentsService: TorrentsService,
    private readonly trackerDiscoveryService: TrackerDiscoveryService,
  ) {}

  async preparePlayback(payload: PreparePlay): Promise<RelayTorrent> {
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

  private async getTorrent(payload: PreparePlay): Promise<RelayTorrent> {
    const { imdbId, tracker, torrentId } = payload;

    const torrentCache = await this.torrentsCacheStore.findOne({
      imdbId,
      tracker,
      torrentId,
    });

    let torrent: RelayTorrent | null = null;

    if (torrentCache) {
      torrent = await this.torrentsService.getTorrentForStream(
        torrentCache.parsed.infoHash,
      );
    }

    if (!torrent) {
      const torrentFile = await this.trackerDiscoveryService.findOneTorrent(
        tracker,
        torrentId,
      );

      torrent = await this.torrentsService.getTorrentForStream(
        torrentFile.infoHash,
      );

      if (!torrent) {
        torrent = await this.torrentsService.addTorrentForStream({
          ...torrentFile,
          torrentFilePath: torrentFile.torrentFilePath,
        });
      }
    }

    return torrent;
  }
}
