import { AudioCodecEnum } from '../../../preference-items/enum/audio-codec.enum';

const AUDIO_CODEC_PATTERNS: Record<
  Exclude<AudioCodecEnum, AudioCodecEnum.UNKNOWN>,
  string[]
> = {
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

export function parseAudioCodec(torrentName: string): AudioCodecEnum {
  const normalizedTorrentName = torrentName.toLocaleLowerCase();

  let audioCodec = AudioCodecEnum.UNKNOWN;

  for (const [type, patterns] of Object.entries(AUDIO_CODEC_PATTERNS)) {
    const isSourceType = patterns.some((pattern) =>
      normalizedTorrentName.includes(pattern),
    );

    if (!isSourceType) {
      continue;
    }

    audioCodec = type as AudioCodecEnum;
    break;
  }

  return audioCodec;
}
