//  @ts-check
import { tanstackConfig } from '@tanstack/eslint-config'

export default [
  ...tanstackConfig,
  {
    rules: {
      'import/order': 'off',
      '@typescript-eslint/array-type': ['error', { default: 'array' }],
    },
  },
]
