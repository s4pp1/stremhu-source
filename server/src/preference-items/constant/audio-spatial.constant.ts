import { AudioSpatialEnum } from '../enum/audio-feature.enum';
import { AudioSpatialOption } from '../type/audio-spatial-option.type';

export const AUDIO_SPATIAL_OPTIONS: AudioSpatialOption[] = [
  { value: AudioSpatialEnum.DTS_X, label: 'DTS:X' },
  { value: AudioSpatialEnum.DOLBY_ATMOS, label: 'Dolby Atmos' },
];

export const AUDIO_SPATIAL_LABEL_MAP = AUDIO_SPATIAL_OPTIONS.reduce(
  (previousValue, value) => ({
    ...previousValue,
    [value.value]: value.label,
  }),
  {} as Record<AudioSpatialEnum, string>,
);
