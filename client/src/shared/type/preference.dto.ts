import type {
  AudioPreferenceDto,
  LanguagePreferenceDto,
  ResolutionPreferenceDto,
  SourcePreferenceDto,
  TrackerPreferenceDto,
  VideoPreferenceDto,
} from '../lib/source-client'

export type PreferenceDto =
  | TrackerPreferenceDto
  | LanguagePreferenceDto
  | ResolutionPreferenceDto
  | VideoPreferenceDto
  | SourcePreferenceDto
  | AudioPreferenceDto
