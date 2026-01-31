import * as z from 'zod'

import {
  AudioCodecEnum,
  LanguageEnum,
  ResolutionEnum,
  SourceTypeEnum,
  VideoQualityEnum,
} from '@/shared/lib/source-client'

export const torrentResolutionsSchema = z.array(z.enum(ResolutionEnum))
export const torrentVideoQualitiesSchema = z.array(z.enum(VideoQualityEnum))
export const torrentAudioCodecsSchema = z.array(z.enum(AudioCodecEnum))
export const torrentSourceTypesSchema = z.array(z.enum(SourceTypeEnum))
export const torrentLanguagesSchema = z.array(z.enum(LanguageEnum))
export const torrentSeedSchema = z.number().nullable()
export const onlyBestTorrentSchema = z.boolean()
