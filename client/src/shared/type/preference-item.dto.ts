import type {
  AudioQualityEnum,
  AudioSpatialEnum,
  LanguageEnum,
  ResolutionEnum,
  SourceEnum,
  TrackerEnum,
  VideoQualityEnum,
} from '../lib/source/source-client'

export type PreferenceItemDto =
  | TrackerEnum[]
  | LanguageEnum[]
  | ResolutionEnum[]
  | VideoQualityEnum[]
  | SourceEnum[]
  | AudioQualityEnum[]
  | AudioSpatialEnum[]
