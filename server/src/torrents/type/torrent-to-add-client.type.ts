import { ParsedTorrent } from 'src/common/utils/parse-torrent.util';
import { TrackerEnum } from 'src/trackers/enum/tracker.enum';

export type TorrentToAddClient = {
  imdbId: string;
  tracker: TrackerEnum;
  torrentId: string;
  parsedTorrent: ParsedTorrent;
};
