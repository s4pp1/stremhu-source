import { VideoQualityEnum } from '../enum/video-quality.enum';

const HDR_PATTERNS: Record<
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

export function parseVideoQualities(torrentName: string): VideoQualityEnum[] {
  const normalizedTorrentName = torrentName.toLocaleLowerCase();

  const videoQualities = Object.entries(HDR_PATTERNS)
    .filter(([, patterns]) =>
      patterns.some((pattern) => normalizedTorrentName.includes(pattern)),
    )
    .map(([type]) => type as VideoQualityEnum);

  return videoQualities.length > 0 ? videoQualities : [VideoQualityEnum.SDR];
}
