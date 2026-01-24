import { TrackerEnum } from 'src/trackers/enum/tracker.enum';

export interface PreparePlay {
  imdbId: string;
  tracker: TrackerEnum;
  torrentId: string;
}
