import { TrackerEnum } from 'src/trackers/enum/tracker.enum';

export type TorrentCacheToCreate = {
  tracker: TrackerEnum;
  torrentId: string;
  torrentBuffer: Buffer;
};
