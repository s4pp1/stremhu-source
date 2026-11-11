import * as z from 'zod'

export const torrentSeedSchema = z.number().nullable()
export const enableSmartFilterSchema = z.boolean()
export const enableStreamDeduplicationSchema = z.boolean()
export const smartFilterLimitSchema = z.number().min(1).max(50)
export const smartFilterGroupingPreferenceIdSchema = z.string().nullable()
export const enableFallbackSubtitlesSchema = z.boolean()
export const enableCatalogSearchSchema = z.boolean()
export const enableDownloadedMarkerSchema = z.boolean()
