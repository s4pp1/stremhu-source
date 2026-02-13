import { SourceEnum } from 'src/preference-items/enum/source.enum';

const SOURCE_TYPE_PATTERNS: Record<
  Exclude<SourceEnum, SourceEnum.UNKNOWN>,
  string[]
> = {
  [SourceEnum.DISC_REMUX]: ['.remux.'],
  [SourceEnum.DISC_RIP]: ['.bluray.', '.bdrip.', '.dvdrip.'],
  [SourceEnum.WEB_DL]: ['.web-dl.', '.web_dl.', '.web-dl-rip.'],
  [SourceEnum.WEB_RIP]: ['.webrip.'],
  [SourceEnum.BROADCAST]: ['.hdtv.', '.pdtv.', '.dvb.', '.satrip.'],
  [SourceEnum.THEATRICAL]: ['.cam.', '.ts.', '.tc.'],
};

export function parseSource(torrentName: string): SourceEnum {
  const normalizedTorrentName = torrentName.toLocaleLowerCase();

  let sourceType = SourceEnum.UNKNOWN;

  for (const [type, patterns] of Object.entries(SOURCE_TYPE_PATTERNS)) {
    const isSourceType = patterns.some((pattern) =>
      normalizedTorrentName.includes(pattern),
    );

    if (!isSourceType) {
      continue;
    }

    sourceType = type as SourceEnum;
    break;
  }

  return sourceType;
}
