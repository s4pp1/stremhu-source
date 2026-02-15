import * as z from 'zod'

import {
  AudioQualityEnum,
  LanguageEnum,
  ResolutionEnum,
  SourceEnum,
  VideoQualityEnum,
} from '@/shared/lib/source-client'

export const torrentResolutionsSchema = z.array(z.enum(ResolutionEnum))
export const torrentVideoQualitiesSchema = z.array(z.enum(VideoQualityEnum))
export const torrentAudioCodecsSchema = z.array(z.enum(AudioQualityEnum))
export const torrentSourceTypesSchema = z.array(z.enum(SourceEnum))
export const torrentLanguagesSchema = z.array(z.enum(LanguageEnum))
export const torrentSeedSchema = z.number().nullable()
export const onlyBestTorrentSchema = z.boolean()
