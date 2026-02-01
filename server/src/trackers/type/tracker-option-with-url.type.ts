import { TrackerOption } from './tracker-option.type';

export type TrackerOptionWithUrl = {
  url: string;
  detailsPath: string;
} & TrackerOption;
