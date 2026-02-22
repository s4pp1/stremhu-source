import { TrackerEnum } from 'src/trackers/enum/tracker.enum';

import { TorrentInfo } from './torrent-info.type';

export type TorrentCache = {
  tracker: TrackerEnum;
  torrentId: string;
  torrentFilePath: string;
  info: TorrentInfo;
};
