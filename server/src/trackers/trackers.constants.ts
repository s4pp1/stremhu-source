import { TrackerEnum } from './enum/tracker.enum';
import { TrackerInfo } from './type/tracker-info.type';
import { TrackerOption } from './type/tracker-option.type';

export const TRACKER_OPTIONS: TrackerOption[] = [
  {
    value: TrackerEnum.NCORE,
    label: 'nCore',
    requiresFullDownload: false,
  },
  {
    value: TrackerEnum.BITHUMEN,
    label: 'BitHUmen',
    requiresFullDownload: false,
  },
  {
    value: TrackerEnum.MAJOMPARADE,
    label: 'Majomparádé',
    requiresFullDownload: true,
  },
];

export const TRACKER_INFO = TRACKER_OPTIONS.reduce(
  (previousValue, value) => ({
    ...previousValue,
    [value.value]: {
      label: value.label,
      requiresFullDownload: value.requiresFullDownload,
    },
  }),
  {} as Record<TrackerEnum, TrackerInfo>,
);

export const LOGIN_ERROR_MESSAGE = 'Hibás felhasználónév, vagy jelszó!';
