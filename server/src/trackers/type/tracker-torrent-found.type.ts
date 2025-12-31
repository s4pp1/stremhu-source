import { TrackerEnum } from '../enum/tracker.enum';

export type TrackerTorrentFound = {
  tracker: TrackerEnum;
  torrentId: string;
  imdbId: string;
  infoHash: string;
  torrentFilePath: string;
};
