import type {
  AudioQualityPreferenceDto,
  AudioSpatialPreferenceDto,
  LanguagePreferenceDto,
  ResolutionPreferenceDto,
  SourcePreferenceDto,
  TrackerPreferenceDto,
  VideoQualityPreferenceDto,
} from '../lib/source-client'

export type PreferenceDto =
  | TrackerPreferenceDto
  | LanguagePreferenceDto
  | ResolutionPreferenceDto
  | VideoQualityPreferenceDto
  | SourcePreferenceDto
  | AudioQualityPreferenceDto
  | AudioSpatialPreferenceDto
