import { TrackerEnum } from 'src/trackers/enum/tracker.enum';
import { TrackerDownload } from 'src/trackers/tracker.types';

import { TorrentInfo } from './type/torrent-info.type';

export interface TorrentsCache {
  imdbId: string;
  tracker: TrackerEnum;
}
export interface TorrentCacheId {
  imdbId: string;
  tracker: TrackerEnum;
  torrentId: string;
}
export interface TorrentCache {
  imdbId: string;
  tracker: TrackerEnum;
  torrentId: string;
  torrentFilePath: string;
  info: TorrentInfo;
}

export interface SaveTorrents {
  downloads: TrackerDownload[];
  imdbId: string;
  tracker: TrackerEnum;
}

export interface ParsedTorrentPath {
  imdbId: string;
  tracker: TrackerEnum;
  torrentId: string;
}
