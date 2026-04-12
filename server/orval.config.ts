import { defineConfig } from 'orval';

// eslint-disable-next-line @typescript-eslint/no-unsafe-call
export default defineConfig({
  relay: {
    input: '../relay/openapi/openapi.json',
    output: {
      mode: 'single',
      target: './src/relay/client/relay-client.ts',
      override: {
        mutator: {
          path: './src/relay/client/relay-client-instance.ts',
          name: 'relayClientInstance',
        },
      },
    },
    hooks: {
      afterAllFilesWrite: 'prettier --write',
    },
  },
  catalog: {
    input: 'https://catalog.stremhu.app/api/docs/public-json',
    output: {
      mode: 'single',
      target: './src/catalog/client/catalog-client.ts',
      override: {
        mutator: {
          path: './src/catalog/client/catalog-client-instance.ts',
          name: 'catalogClientInstance',
        },
      },
    },
    hooks: {
      afterAllFilesWrite: 'prettier --write',
    },
  },
});
