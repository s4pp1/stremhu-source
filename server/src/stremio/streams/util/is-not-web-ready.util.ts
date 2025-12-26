import { VideoCodec as VideoCodecEnum } from '@ctrl/video-filename-parser';

import { AudioCodecEnum } from '../enum/audio-codec.enum';

const AUDIO_CODEC = {
  MP3: 'MP3',
  MP2: 'MP2',
  DOLBY: 'Dolby Digital',
  EAC3: 'Dolby Digital Plus',
  AAC: 'AAC',
  FLAC: 'FLAC',
  DTS: 'DTS',
  DTSHD: 'DTS-HD',
  TRUEHD: 'Dolby TrueHD',
  OPUS: 'Opus',
  VORBIS: 'Vorbis',
  PCM: 'PCM',
  LPCM: 'LPCM',
};

export function isNotWebReady(
  videoCodec: VideoCodecEnum | undefined,
  audioCodec: AudioCodecEnum | undefined,
): boolean {
  return notWebReadyVideoCodec(videoCodec) || notWebReadyAudioCodec(audioCodec);
}

function notWebReadyVideoCodec(
  videoCodec: VideoCodecEnum | undefined,
): boolean {
  if (!videoCodec) return false;

  const notSupportedCodecs = [
    VideoCodecEnum.H265,
    VideoCodecEnum.X265,
    VideoCodecEnum.WMV,
    VideoCodecEnum.XVID,
    VideoCodecEnum.DVDR,
  ];

  return notSupportedCodecs.includes(videoCodec);
}

function notWebReadyAudioCodec(audioCodec: AudioCodecEnum | undefined) {
  if (!audioCodec) return false;

  const notSupportedCodecs = [
    AUDIO_CODEC.FLAC,
    AUDIO_CODEC.MP2,
    AUDIO_CODEC.DOLBY,
    AUDIO_CODEC.EAC3,
    AUDIO_CODEC.DTS,
    AUDIO_CODEC.DTSHD,
    AUDIO_CODEC.TRUEHD,
  ] as AudioCodecEnum[];

  return notSupportedCodecs.includes(audioCodec);
}
