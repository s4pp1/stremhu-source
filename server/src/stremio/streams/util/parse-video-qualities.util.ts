import { VideoQualityEnum } from '../enum/video-quality.enum';

type HdrType =
  | VideoQualityEnum.DV
  | VideoQualityEnum.HDR10
  | VideoQualityEnum.HDR10P
  | VideoQualityEnum.HLG;

const HDR_PATTERNS: Record<HdrType, string[]> = {
  [VideoQualityEnum.DV]: [
    '.Dolby.Vision.',
    '.DoVi.',
    '.DoVi-',
    '-DoVi.',
    '.DV.',
  ],
  [VideoQualityEnum.HDR10]: [
    '.HDR.',
    '-HDR.',
    '.HDR-',
    '.HDR10.',
    '-HDR10.',
    '.HDR10-',
  ],
  [VideoQualityEnum.HDR10P]: [
    '.HDR10Plus.',
    '-HDR10Plus.',
    '.HDR10Plus-',
    '.HDR10+.',
    '-HDR10+.',
    '.HDR10+-',
    '.HDR10P.',
    '-HDR10P.',
    '.HDR10P-',
  ],
  [VideoQualityEnum.HLG]: ['.HLG.'],
};

export function parseVideoQualities(torrentName: string): VideoQualityEnum[] {
  const videoQualities = Object.entries(HDR_PATTERNS)
    .filter(([, patterns]) =>
      patterns.some((pattern) => torrentName.includes(pattern)),
    )
    .map(([type]) => type as VideoQualityEnum);

  return videoQualities.length > 0 ? videoQualities : [VideoQualityEnum.SDR];
}
