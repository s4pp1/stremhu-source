import { i18n } from '@lingui/core'

export const locales = {
  en: 'English',
  hu: 'Magyar',
}

export const defaultLocale = 'en'

export async function dynamicActivate(locale: string) {
  try {
    // The .po files are compiled on the fly by @lingui/vite-plugin
    const { messages } = await import(`../../locales/${locale}/messages.po`)
    i18n.load(locale, messages)
    i18n.activate(locale)
  } catch (error) {
    console.error(`Error loading locale ${locale}:`, error)
  }
}
