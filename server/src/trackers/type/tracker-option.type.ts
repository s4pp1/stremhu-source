import { TrackerEnum } from '../enum/tracker.enum';
import { TrackerInfo } from './tracker-info.type';

export type TrackerOption = {
  value: TrackerEnum;
} & TrackerInfo;
