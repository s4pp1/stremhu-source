import { ParsedTorrent } from 'src/common/utils/parse-torrent.util';
import { TrackerEnum } from 'src/trackers/enum/tracker.enum';

export interface WebTorrentToAdd {
  imdbId: string;
  tracker: TrackerEnum;
  torrentId: string;
  parsed: ParsedTorrent;
}

export interface ActiveTorrent {
  name: string;
  infoHash: string;
  downloaded: number;
  progress: number;
  total: number;
  uploaded: number;
  uploadSpeed: number;

  imdbId: string;
  tracker: TrackerEnum;
  torrentId: string;

  updatedAt: Date;
  createdAt: Date;
}
