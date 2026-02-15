import { TrackerEnum } from '../enum/tracker.enum';

export type TrackerOption = {
  value: TrackerEnum;
  label: string;
  requiresFullDownload: boolean;
  url: string;
  detailsPath: string;
};
