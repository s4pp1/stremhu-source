import { SourceEnum } from 'src/preference-items/enum/source.enum';

const PATTERNS: Record<Exclude<SourceEnum, SourceEnum.UNKNOWN>, string[]> = {
  [SourceEnum.DISC_REMUX]: ['.remux.'],
  [SourceEnum.DISC_RIP]: ['.bluray.', '.bdrip.', '.dvdrip.'],
  [SourceEnum.WEB_DL]: ['.web-dl.', '.web_dl.', '.web-dl-rip.'],
  [SourceEnum.WEB_RIP]: ['.webrip.'],
  [SourceEnum.BROADCAST]: ['.hdtv.', '.pdtv.', '.dvb.', '.satrip.'],
  [SourceEnum.THEATRICAL]: ['.cam.', '.ts.', '.tc.'],
};

export function parseSource(name: string): SourceEnum {
  for (const [type, patterns] of Object.entries(PATTERNS)) {
    const isMatched = patterns.some((pattern) => name.includes(pattern));

    if (isMatched) {
      return type as SourceEnum;
    }
  }

  return SourceEnum.UNKNOWN;
}
