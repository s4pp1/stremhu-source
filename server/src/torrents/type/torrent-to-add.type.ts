import { TrackerEnum } from 'src/trackers/enum/tracker.enum';

export type TorrentToAdd = {
  tracker: TrackerEnum;
  torrentId: string;
  torrentFilePath: string;
};
