import { Resolution as ResolutionEnum } from '@ctrl/video-filename-parser';

import { ResolutionOption } from '../type/resolution-option.type';

export const RESOLUTION_OPTIONS: ResolutionOption[] = [
  { value: ResolutionEnum.R2160P, label: 'UHD (4K)' },
  { value: ResolutionEnum.R1080P, label: 'Full HD (1080p)' },
  { value: ResolutionEnum.R720P, label: 'HD (720p)' },
  { value: ResolutionEnum.R576P, label: 'SD (576p)' },
  { value: ResolutionEnum.R540P, label: 'SD (540p)' },
  { value: ResolutionEnum.R480P, label: 'SD (480p)' },
];

export const ALL_RESOLUTION = RESOLUTION_OPTIONS.map(
  (resolution) => resolution.value,
);

export const RESOLUTION_LABEL_MAP = RESOLUTION_OPTIONS.reduce(
  (previousValue, value) => ({
    ...previousValue,
    [value.value]: value.label,
  }),
  {} as Record<ResolutionEnum, string>,
);
