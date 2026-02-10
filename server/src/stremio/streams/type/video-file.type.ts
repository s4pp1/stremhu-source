import {
  Resolution as ResolutionEnum,
  Source as SourceEnum,
  VideoCodec as VideoCodecEnum,
} from '@ctrl/video-filename-parser';

import { LanguageEnum } from 'src/preference-items/enum/language.enum';
import { TrackerEnum } from 'src/trackers/enum/tracker.enum';

import { AudioCodecEnum } from '../../../preference-items/enum/audio-codec.enum';
import { SourceTypeEnum } from '../../../preference-items/enum/source-type.enum';
import { VideoQualityEnum } from '../../../preference-items/enum/video-quality.enum';

export type VideoFile = {
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
  audioCodec: AudioCodecEnum;
  videoQualities: VideoQualityEnum[];
  sourceType: SourceTypeEnum;
  sources: SourceEnum[];
  notWebReady: boolean;
};
