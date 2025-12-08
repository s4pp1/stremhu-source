import * as z from 'zod'

import { LanguageEnum, ResolutionEnum } from '@/shared/lib/source-client'

export const userPreferencesSchema = z.object({
  torrentResolutions: z.array(z.enum(ResolutionEnum)),
  torrentLanguages: z.array(z.enum(LanguageEnum)),
  torrentSeed: z.number().nullable(),
})
