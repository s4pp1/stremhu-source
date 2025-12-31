import { ParsedTorrent } from 'src/common/utils/parse-torrent.util';
import { TrackerEnum } from 'src/trackers/enum/tracker.enum';
import { TrackerDownload } from 'src/trackers/tracker.types';

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
  parsed: ParsedTorrent;
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
