import { VideoQualityEnum } from '../../../../../preference-items/enum/video-quality.enum';

const PATTERNS: Record<
  Exclude<VideoQualityEnum, VideoQualityEnum.SDR>,
  string[]
> = {
  [VideoQualityEnum.DV]: [
    '.dolby.vision.',
    '.dovi.',
    '.dovi-',
    '-dovi.',
    '.dv.',
  ],
  [VideoQualityEnum.HDR10]: [
    '.hdr.',
    '-hdr.',
    '.hdr-',
    '.hdr10.',
    '-hdr10.',
    '.hdr10-',
  ],
  [VideoQualityEnum.HDR10P]: [
    '.hdr10plus.',
    '-hdr10plus.',
    '.hdr10plus-',
    '.hdr10+.',
    '-hdr10+.',
    '.hdr10+-',
    '.hdr10p.',
    '-hdr10p.',
    '.hdr10p-',
  ],
  [VideoQualityEnum.HLG]: ['.hlg.'],
};

export function parseVideoQuality(name: string): VideoQualityEnum[] {
  const items = Object.entries(PATTERNS)
    .filter(([, patterns]) =>
      patterns.some((pattern) => name.includes(pattern)),
    )
    .map(([type]) => type as VideoQualityEnum);

  if (items.length === 0) {
    return [VideoQualityEnum.SDR];
  }

  return items;
}
