import { TrackerEnum } from './enums/tracker.enum';
import { TrackerOption } from './tracker.types';

export const TRACKER_OPTIONS: TrackerOption[] = [
  { value: TrackerEnum.NCORE, label: 'nCore' },
  { value: TrackerEnum.BITHUMEN, label: 'bitHUmen' },
];

export const TRACKER_LABEL_MAP = TRACKER_OPTIONS.reduce(
  (previousValue, value) => ({
    ...previousValue,
    [value.value]: value.label,
  }),
  {} as Record<TrackerEnum, string>,
);
