import { TrackerEnum } from 'src/trackers/enum/tracker.enum';

export type TorrentToAdd = {
  imdbId: string;
  tracker: TrackerEnum;
  torrentId: string;
  torrentFilePath: string;
};
