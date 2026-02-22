import { TrackerEnum } from 'src/trackers/enum/tracker.enum';

export type TorrentCacheId = {
  tracker: TrackerEnum;
  torrentId: string;
};
