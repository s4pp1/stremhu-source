import { ParsedTorrent } from 'src/common/utils/parse-torrent.util';
import { TrackerEnum } from 'src/trackers/enum/tracker.enum';

export type TorrentCacheToCreate = {
  tracker: TrackerEnum;
  torrentId: string;
  imdbId: string;
  parsed: ParsedTorrent;
};
