import { AudioCodecEnum } from 'src/stremio/streams/enum/audio-codec.enum';

import { AudioCodecOption } from '../type/audio-codec-option.type';

export const AUDIO_CODEC_OPTIONS: AudioCodecOption[] = [
  { value: AudioCodecEnum.TRUEHD, label: 'Dolby TrueHD' },
  { value: AudioCodecEnum.DTS_HD_MA, label: 'DTS-HD Master Audio' },
  { value: AudioCodecEnum.DD_PLUS, label: 'Dolby Digital Plus' },
  { value: AudioCodecEnum.DTS, label: 'DTS Core' },
  { value: AudioCodecEnum.DD, label: 'Dolby Digital' },
  { value: AudioCodecEnum.AAC, label: 'AAC' },
  { value: AudioCodecEnum.UNKNOWN, label: 'Ismeretlen' },
];

export const AUDIO_CODEC_LABEL_MAP = AUDIO_CODEC_OPTIONS.reduce(
  (previousValue, value) => ({
    ...previousValue,
    [value.value]: value.label,
  }),
  {} as Record<AudioCodecEnum, string>,
);
