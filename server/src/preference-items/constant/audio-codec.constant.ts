import { AudioQualityEnum } from 'src/preference-items/enum/audio-quality.enum';

import { AudioQualityOption } from '../type/audio-codec-option.type';

export const AUDIO_QUALITY_OPTIONS: AudioQualityOption[] = [
  { value: AudioQualityEnum.TRUEHD, label: 'Dolby TrueHD' },
  { value: AudioQualityEnum.DTS_HD_MA, label: 'DTS-HD Master Audio' },
  { value: AudioQualityEnum.DD_PLUS, label: 'Dolby Digital Plus' },
  { value: AudioQualityEnum.DTS, label: 'DTS Core' },
  { value: AudioQualityEnum.DD, label: 'Dolby Digital' },
  { value: AudioQualityEnum.AAC, label: 'AAC' },
  { value: AudioQualityEnum.UNKNOWN, label: 'Egyéb' },
];

export const AUDIO_QUALITY_LABEL_MAP = AUDIO_QUALITY_OPTIONS.reduce(
  (previousValue, value) => ({
    ...previousValue,
    [value.value]: value.label,
  }),
  {} as Record<AudioQualityEnum, string>,
);
