import { ResolutionEnum } from 'src/preference-items/enum/resolution.enum';

const PATTERNS: Record<ResolutionEnum, RegExp> = {
  [ResolutionEnum.R2160P]:
    /(?<R2160P>2160p|4k[-_. ](?:UHD|HEVC|BD)|(?:UHD|HEVC|BD)[-_. ]4k|\b(4k)\b|COMPLETE.UHD|UHD.COMPLETE)/i,
  [ResolutionEnum.R1080P]: /(?<R1080P>1080(i|p)|1920x1080)(10bit)?/i,
  [ResolutionEnum.R720P]: /(?<R720P>720(i|p)|1280x720|960p)(10bit)?/i,
  [ResolutionEnum.R576P]: /(?<R576P>576(i|p))/i,
  [ResolutionEnum.R540P]: /(?<R540P>540(i|p))/i,
  [ResolutionEnum.R480P]: /(?<R480P>480(i|p)|640x480|848x480)/i,
};

export function parseResolution(
  name: string,
  fallback: ResolutionEnum,
): ResolutionEnum {
  for (const [type, pattern] of Object.entries(PATTERNS)) {
    if (pattern.test(name)) {
      return type as ResolutionEnum;
    }
  }

  return fallback;
}
