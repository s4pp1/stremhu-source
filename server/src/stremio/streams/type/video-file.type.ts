import { AudioSpatialEnum } from 'src/preference-items/enum/audio-feature.enum';
import { AudioQualityEnum } from 'src/preference-items/enum/audio-quality.enum';
import { LanguageEnum } from 'src/preference-items/enum/language.enum';
import { ResolutionEnum } from 'src/preference-items/enum/resolution.enum';
import { SourceEnum } from 'src/preference-items/enum/source.enum';
import { VideoQualityEnum } from 'src/preference-items/enum/video-quality.enum';
import { PreferenceEnum } from 'src/preferences/enum/preference.enum';
import { TrackerEnum } from 'src/trackers/enum/tracker.enum';

export type VideoFile = {
  [PreferenceEnum.TRACKER]: TrackerEnum;
  torrentId: string;
  seeders: number;

  torrentName: string;
  infoHash: string;
  fileName: string;
  fileSize: number;
  fileIndex: number;

  [PreferenceEnum.LANGUAGE]: LanguageEnum;
  [PreferenceEnum.RESOLUTION]: ResolutionEnum;
  [PreferenceEnum.VIDEO_QUALITY]: VideoQualityEnum[];
  [PreferenceEnum.AUDIO_QUALITY]: AudioQualityEnum;
  [PreferenceEnum.AUDIO_SPATIAL]: AudioSpatialEnum | null;
  [PreferenceEnum.SOURCE]: SourceEnum;

  notWebReady: boolean;
};
