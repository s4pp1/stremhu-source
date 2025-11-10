import {
  ParsedFilename,
  Resolution as ResolutionEnum,
  Source as SourceEnum,
  VideoCodec as VideoCodecEnum,
} from '@ctrl/video-filename-parser';

import { LanguageEnum } from 'src/common/enums/language.enum';
import { ParsedFile } from 'src/common/utils/parse-torrent.util';
import { TrackerEnum } from 'src/trackers/enums/tracker.enum';
import { User } from 'src/users/entities/user.entity';

import { StreamMediaTypeEnum } from '../enums/stream-media-type.enum';
import { ParsedStreamIdSeries } from './pipe/stream-id.pipe';

export enum RangeErrorEnum {
  RANGE_NOT_DEFINED = 'range-not-defined',
  RANGE_NOT_SATISFIABLE = 'range-not-satisfiable',
  RANGE_MALFORMED = 'range-malformed',
}

export interface CalculateRange {
  rangeHeader?: string;
  total: number;
  torrentPieceLength: number;
}

export interface CalculatedRangeDetails {
  start: number;
  end: number;
  contentLength: number;
}

export type CalculatedRange = CalculatedRangeDetails | RangeErrorEnum;

export type AudioCodecEnum = NonNullable<ParsedFilename['audioCodec']>;

export const AudioCodecConst = {
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
} as const;

export interface VideoFileResolution {
  label: string;
  value: ResolutionEnum;
  rank: number;
}

export interface VideoFileLanguage {
  emoji: string;
  label: string;
  value: LanguageEnum;
  rank: number;
}

export interface VideoFileWithRank {
  imdbId: string;
  tracker: TrackerEnum;
  torrentId: string;
  seeders: number;

  infoHash: string;
  fileName: string;
  fileSize: number;
  fileIndex: number;

  resolution: VideoFileResolution;
  language: VideoFileLanguage;
  videoCodec?: VideoCodecEnum;
  audioCodec?: AudioCodecEnum;
  sources: SourceEnum[];
  notWebReady: boolean;
}

export interface FindStreams {
  user: User;
  mediaType: StreamMediaTypeEnum;
  imdbId: string;
  series?: ParsedStreamIdSeries;
}

export interface PlayStream {
  imdbId: string;
  tracker: TrackerEnum;
  torrentId: string;
  fileIdx: number;
}

export interface SelectVideoOptions {
  files: ParsedFile[] | undefined;
  series?: ParsedStreamIdSeries;
}

export interface SelectedVideoFile {
  fileIndex: number;
  file: ParsedFile;
}
