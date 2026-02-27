import { AudioQualityOption } from 'src/preference-items/type/audio-codec-option.type';
import { AudioSpatialOption } from 'src/preference-items/type/audio-spatial-option.type';
import { LanguageOption } from 'src/preference-items/type/language-option.type';
import { ResolutionOption } from 'src/preference-items/type/resolution-option.type';
import { SourceOption } from 'src/preference-items/type/source-option.type';
import { VideoQualityOption } from 'src/preference-items/type/video-quality-option.type';
import { PreferenceEnum } from 'src/preferences/enum/preference.enum';

import { BaseTorrentVideo } from './base-torrent-video.type';

export type TorrentVideo = BaseTorrentVideo & {
  seeders: number;

  [PreferenceEnum.LANGUAGE]: LanguageOption;
  [PreferenceEnum.RESOLUTION]: ResolutionOption;
  [PreferenceEnum.VIDEO_QUALITY]: VideoQualityOption[];
  [PreferenceEnum.AUDIO_QUALITY]?: AudioQualityOption;
  [PreferenceEnum.AUDIO_SPATIAL]?: AudioSpatialOption;
  [PreferenceEnum.SOURCE]: SourceOption;

  isInRelay: boolean;
};
