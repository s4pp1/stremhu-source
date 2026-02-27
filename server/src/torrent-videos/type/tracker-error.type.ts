import { TrackerOption } from 'src/trackers/type/tracker-option.type';

export type TrackerError = {
  tracker: TrackerOption;
  message: string;
};
