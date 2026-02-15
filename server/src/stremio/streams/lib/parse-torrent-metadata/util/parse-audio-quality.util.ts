import { AudioQualityEnum } from 'src/preference-items/enum/audio-quality.enum';

const AUDIO_QUALITY_PATTERNS: Record<
  Exclude<AudioQualityEnum, AudioQualityEnum.UNKNOWN>,
  string[]
> = {
  [AudioQualityEnum.TRUEHD]: ['.truehd.'],
  [AudioQualityEnum.DTS_HD_MA]: ['.dts-hd.ma.', '.dtshdma.', '.dts-hdma.'],
  [AudioQualityEnum.DD_PLUS]: [
    '.ddp.',
    '.ddp5.1.',
    '.ddp7.1.',
    '.dd+.',
    '.dd+5.1.',
    '.dd+7.1.',
    '.eac3.',
  ],
  [AudioQualityEnum.DTS]: ['.dts.', '.dts5.1.'],
  [AudioQualityEnum.DD]: [
    '.dd.',
    '.dd2.0.',
    '.dd5.1.',
    '.dd7.1.',
    '.ac3.',
    '.ac-3.',
  ],
  [AudioQualityEnum.AAC]: ['.aac.', '.aac2.0.', '.aac5.1.'],
};

export function parseAudioQuality(name: string): AudioQualityEnum {
  for (const [type, patterns] of Object.entries(AUDIO_QUALITY_PATTERNS)) {
    const isMatched = patterns.some((pattern) => name.includes(pattern));

    if (isMatched) {
      return type as AudioQualityEnum;
    }
  }

  return AudioQualityEnum.UNKNOWN;
}
