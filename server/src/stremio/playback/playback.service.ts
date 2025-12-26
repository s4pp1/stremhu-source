import { Injectable } from '@nestjs/common';
import { TorrentFile } from 'webtorrent';

import { WebTorrentTorrent } from 'src/clients/webtorrent/webtorrent.types';
import { TorrentsCacheStore } from 'src/torrents-cache/core/torrents-cache.store';
import { TorrentsService } from 'src/torrents/torrents.service';
import { TrackerDiscoveryService } from 'src/trackers/tracker-discovery.service';

import { Play } from './type/play.type';

@Injectable()
export class PlaybackService {
  private inFlightPlay = new Map<string, Promise<TorrentFile>>();

  constructor(
    private readonly torrentsCacheStore: TorrentsCacheStore,
    private readonly torrentsService: TorrentsService,
    private readonly trackerDiscoveryService: TrackerDiscoveryService,
  ) {}

  async play(payload: Play): Promise<TorrentFile> {
    const { imdbId, tracker, torrentId, fileIndex } = payload;

    const key = `${imdbId}-${tracker}-${torrentId}-${fileIndex}`;
    const running = this.inFlightPlay.get(key);
    if (running) return running;

    const promise = this.getTorrentFile(payload);

    this.inFlightPlay.set(key, promise);

    try {
      const response = await promise;
      return response;
    } finally {
      this.inFlightPlay.delete(key);
    }
  }

  private async getTorrentFile(payload: Play): Promise<TorrentFile> {
    const { imdbId, tracker, torrentId, fileIndex } = payload;

    const torrentCache = await this.torrentsCacheStore.findOne({
      imdbId,
      tracker,
      torrentId,
    });

    let torrent: WebTorrentTorrent | null = null;

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
        torrentFile.parsed.infoHash,
      );

      if (!torrent) {
        torrent = await this.torrentsService.addTorrentForStream({
          ...torrentFile,
          parsedTorrent: torrentFile.parsed,
        });
      }
    }

    const file = this.torrentsService.getTorrentFileForStream(
      torrent,
      fileIndex,
    );

    return file;
  }
}
