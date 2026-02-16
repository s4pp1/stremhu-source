import type {
  AudioQualityPreferenceMetaDto,
  LanguagePreferenceMetaDto,
  ResolutionPreferenceMetaDto,
  SourcePreferenceMetaDto,
  TrackerPreferenceMetaDto,
  VideoQualityPreferenceMetaDto,
} from '../lib/source-client'

export type PreferenceMetaDto =
  | TrackerPreferenceMetaDto
  | LanguagePreferenceMetaDto
  | ResolutionPreferenceMetaDto
  | VideoQualityPreferenceMetaDto
  | SourcePreferenceMetaDto
  | AudioQualityPreferenceMetaDto
