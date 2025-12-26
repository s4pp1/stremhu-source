import {
  Resolution as ResolutionEnum,
  Source as SourceEnum,
  VideoCodec as VideoCodecEnum,
} from '@ctrl/video-filename-parser';

import { LanguageEnum } from 'src/common/enum/language.enum';
import { TrackerEnum } from 'src/trackers/enum/tracker.enum';

import { AudioCodecEnum } from '../enum/audio-codec.enum';
import { VideoQualityEnum } from '../enum/video-quality.enum';

export type VideoFileWithRank = {
  imdbId: string;
  tracker: TrackerEnum;
  torrentId: string;
  seeders: number;
  group?: string;

  infoHash: string;
  fileName: string;
  fileSize: number;
  fileIndex: number;

  resolution: ResolutionEnum;
  language: LanguageEnum;
  videoCodec?: VideoCodecEnum;
  audioCodec?: AudioCodecEnum;
  videoQualities: VideoQualityEnum[];
  sources: SourceEnum[];
  notWebReady: boolean;
};
