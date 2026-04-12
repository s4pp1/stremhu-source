import { PreferenceEnum } from '@/shared/lib/source/source-client'
import type { PreferenceDto } from '@/shared/type/preference.dto'

export const preferenceFormValues: PreferenceDto = {
  preference: PreferenceEnum.language,
  preferred: [],
  blocked: [],
}
