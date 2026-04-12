import type {
  AudioQualityMetaDto,
  AudioSpatialMetaDto,
  LanguageMetaDto,
  ResolutionMetaDto,
  SourceMetaDto,
  TrackerMetaDto,
  VideoQualityMetaDto,
} from '../lib/source/source-client'

export type PreferenceItemMeta =
  | TrackerMetaDto
  | LanguageMetaDto
  | ResolutionMetaDto
  | VideoQualityMetaDto
  | SourceMetaDto
  | AudioQualityMetaDto
  | AudioSpatialMetaDto
