import * as z from 'zod'

import {
  LanguageEnum,
  ResolutionEnum,
  VideoQualityEnum,
} from '@/shared/lib/source-client'

export const torrentResolutionsSchema = z.array(z.enum(ResolutionEnum))
export const torrentVideoQualitiesSchema = z.array(z.enum(VideoQualityEnum))
export const torrentLanguagesSchema = z.array(z.enum(LanguageEnum))
export const torrentSeedSchema = z.number().nullable()
export const onlyBestTorrentSchema = z.boolean()
