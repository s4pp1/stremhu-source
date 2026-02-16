import type {
  AudioQualityEnum,
  LanguageEnum,
  ResolutionEnum,
  SourceEnum,
  TrackerEnum,
  VideoQualityEnum,
} from '../lib/source-client'

export type PreferenceItemDto =
  | Array<TrackerEnum>
  | Array<LanguageEnum>
  | Array<ResolutionEnum>
  | Array<VideoQualityEnum>
  | Array<SourceEnum>
  | Array<AudioQualityEnum>
