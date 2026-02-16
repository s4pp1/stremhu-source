import { PreferenceEnum } from '@/shared/lib/source-client'
import type { PreferenceDto } from '@/shared/type/preference.dto'

export const preferenceFormValues: PreferenceDto = {
  preference: PreferenceEnum.LANGUAGE,
  preferred: [],
  blocked: [],
}
