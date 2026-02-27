import { TrackerEnum } from 'src/trackers/enum/tracker.enum';

export interface PreparePlay {
  tracker: TrackerEnum;
  torrentId: string;
}
