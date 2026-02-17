import { AudioSpatialEnum } from 'src/preference-items/enum/audio-feature.enum';

const PATTERNS: Record<AudioSpatialEnum, string[]> = {
  [AudioSpatialEnum.DTS_X]: [
    '.dtsx.',
    '.dtsx.7.1.',
    '.dts.x.',
    '.dts.x7.1.',
    '.dts.x.7.1.',
  ],
  [AudioSpatialEnum.DOLBY_ATMOS]: ['.atmos.'],
};

export function parseAudioSpatial(name: string): AudioSpatialEnum | null {
  for (const [type, patterns] of Object.entries(PATTERNS)) {
    const isMatched = patterns.some((pattern) => name.includes(pattern));

    if (isMatched) {
      return type as AudioSpatialEnum;
    }
  }

  return null;
}
