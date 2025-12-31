import { TrackerEnum } from 'src/trackers/enum/tracker.enum';

export type TorrentToAddClient = {
  imdbId: string;
  tracker: TrackerEnum;
  torrentId: string;
  torrentFilePath: string;
};
