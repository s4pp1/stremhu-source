import { VideoQualityEnum } from 'src/preference-items/enum/video-quality.enum';

import { VideoQualityOption } from '../type/video-quality-option.type';

export const VIDEO_QUALITY_OPTIONS: VideoQualityOption[] = [
  { value: VideoQualityEnum.DV, label: 'Dolby Vision' },
  { value: VideoQualityEnum.HDR10P, label: 'HDR10+' },
  { value: VideoQualityEnum.HDR10, label: 'HDR10' },
  { value: VideoQualityEnum.HLG, label: 'HLG' },
  { value: VideoQualityEnum.SDR, label: 'SDR' },
];

export const VIDEO_QUALITY_LABEL_MAP = VIDEO_QUALITY_OPTIONS.reduce(
  (previouItems, item) => ({
    ...previouItems,
    [item.value]: item.label,
  }),
  {} as Record<VideoQualityEnum, string>,
);
