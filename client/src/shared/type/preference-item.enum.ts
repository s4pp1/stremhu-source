import type {
  AudioQualityEnum,
  AudioSpatialEnum,
  LanguageEnum,
  ResolutionEnum,
  SourceEnum,
  TrackerEnum,
  VideoQualityEnum,
} from '../lib/source/source-client'

export type PreferenceItemEnum =
  | TrackerEnum
  | LanguageEnum
  | ResolutionEnum
  | VideoQualityEnum
  | SourceEnum
  | AudioQualityEnum
  | AudioSpatialEnum
