import { AudioCodecEnum } from '../enum/audio-codec.enum';

const AUDIO_CODEC_PATTERNS: Record<AudioCodecEnum, string[]> = {
  [AudioCodecEnum.TRUEHD]: ['.truehd.'],
  [AudioCodecEnum.DTS_HD_MA]: ['.dts-hd.ma.', '.dtshdma.', '.dts-hdma.'],
  [AudioCodecEnum.DD_PLUS]: [
    '.ddp.',
    '.ddp5.1.',
    '.ddp7.1.',
    '.dd+.',
    '.dd+5.1.',
    '.dd+7.1.',
    '.eac3.',
  ],
  [AudioCodecEnum.DTS]: ['.dts.', '.dts5.1.'],
  [AudioCodecEnum.DD]: [
    '.dd.',
    '.dd2.0.',
    '.dd5.1.',
    '.dd7.1.',
    '.ac3.',
    '.ac-3.',
  ],
  [AudioCodecEnum.AAC]: ['.aac.', '.aac2.0.', '.aac5.1.'],
};

export function parseAudioCodecs(torrentName: string): AudioCodecEnum[] {
  const normalizedTorrentName = torrentName.toLocaleLowerCase();

  const audioCodecs = Object.entries(AUDIO_CODEC_PATTERNS)
    .filter(([, patterns]) =>
      patterns.some((pattern) => normalizedTorrentName.includes(pattern)),
    )
    .map(([type]) => type as AudioCodecEnum);

  return audioCodecs.length > 0 ? audioCodecs : [];
}
