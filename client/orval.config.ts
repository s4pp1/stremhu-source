import { defineConfig } from 'orval'

export default defineConfig({
  source: {
    input: '../server/openapi/openapi.json',
    output: {
      mode: 'single',
      target: './src/shared/lib/source/source-client.ts',
      override: {
        mutator: {
          path: './src/shared/lib/source/source-client-instance.ts',
          name: 'sourceClientInstance',
        },
      },
    },
    hooks: {
      afterAllFilesWrite: 'prettier --write',
    },
  },
})
