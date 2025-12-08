import { QueryClient } from '@tanstack/react-query'

import { SourceClient } from './source-client/SourceClient'

export const appClient = new SourceClient({
  WITH_CREDENTIALS: true,
})

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000,
      gcTime: 10 * 60 * 1000,
    },
  },
})
