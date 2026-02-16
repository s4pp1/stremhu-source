import { AudioQualityEnum } from 'src/preference-items/enum/audio-quality.enum';
import { LanguageEnum } from 'src/preference-items/enum/language.enum';
import { ResolutionEnum } from 'src/preference-items/enum/resolution.enum';
import { SourceEnum } from 'src/preference-items/enum/source.enum';
import { VideoQualityEnum } from 'src/preference-items/enum/video-quality.enum';
import { TrackerEnum } from 'src/trackers/enum/tracker.enum';

import { PreferenceEnum } from '../enum/preference.enum';

export class TrackerPreference {
  preference: PreferenceEnum.TRACKER;

  preferred: TrackerEnum[];

  blocked: TrackerEnum[];
}

export class LanguagePreference {
  preference: PreferenceEnum.LANGUAGE;

  preferred: LanguageEnum[];

  blocked: LanguageEnum[];
}

export class ResolutionPreference {
  preference: PreferenceEnum.RESOLUTION;

  preferred: ResolutionEnum[];

  blocked: ResolutionEnum[];
}

export class VideoPreference {
  preference: PreferenceEnum.VIDEO_QUALITY;

  preferred: VideoQualityEnum[];

  blocked: VideoQualityEnum[];
}

export class SourcePreference {
  preference: PreferenceEnum.SOURCE;

  preferred: SourceEnum[];

  blocked: SourceEnum[];
}

export class AudioPreference {
  preference: PreferenceEnum.AUDIO_QUALITY;

  preferred: AudioQualityEnum[];

  blocked: AudioQualityEnum[];
}

export type Preference = {
  order: number | null;
} & (
  | TrackerPreference
  | LanguagePreference
  | ResolutionPreference
  | VideoPreference
  | SourcePreference
  | AudioPreference
);
