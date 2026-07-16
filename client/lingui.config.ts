import type { LinguiConfig } from '@lingui/conf'
import { formatter } from '@lingui/format-po'

const config: LinguiConfig = {
  locales: ['en', 'hu'],
  sourceLocale: 'en',
  catalogs: [
    {
      path: '<rootDir>/src/locales/{locale}/messages',
      include: ['src'],
    },
  ],
  format: formatter(),
}

export default config
