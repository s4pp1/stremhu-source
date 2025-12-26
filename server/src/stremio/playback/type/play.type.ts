import { TrackerEnum } from 'src/trackers/enum/tracker.enum';

export interface Play {
  imdbId: string;
  tracker: TrackerEnum;
  torrentId: string;
  fileIndex: number;
}
