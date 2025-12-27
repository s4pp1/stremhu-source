import { TrackerEnum } from 'src/trackers/enum/tracker.enum';

export type TrackerCoreToCreate = {
  tracker: TrackerEnum;
  username: string;
  password: string;
  hitAndRun: boolean | null;
  keepSeedSeconds: number | null;
  downloadFullTorrent: boolean;
  orderIndex: number;
};
