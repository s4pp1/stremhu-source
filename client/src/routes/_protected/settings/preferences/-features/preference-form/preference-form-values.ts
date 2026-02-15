import { PreferenceEnum } from '@/shared/lib/source-client'
import type { PreferenceDto } from '@/shared/queries/me-preferences'

export const preferenceFormValues: PreferenceDto = {
  preference: PreferenceEnum.LANGUAGE,
  preferred: [],
  blocked: [],
}
