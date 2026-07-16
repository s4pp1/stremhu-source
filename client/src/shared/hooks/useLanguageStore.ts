import { create } from 'zustand'
import { persist } from 'zustand/middleware'

import { defaultLocale, dynamicActivate } from '../i18n'

interface LanguageState {
  locale: string
  setLocale: (locale: string) => Promise<void>
}

export const useLanguageStore = create<LanguageState>()(
  persist(
    (set) => ({
      locale: defaultLocale,
      setLocale: async (newLocale: string) => {
        await dynamicActivate(newLocale)
        set({ locale: newLocale })
      },
    }),
    {
      name: 'stremhu-language-storage',
    },
  ),
)
