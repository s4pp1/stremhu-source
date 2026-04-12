import { queryOptions } from '@tanstack/react-query'

import { setupStatus } from '../lib/source/source-client'

export const getSettingsStatus = queryOptions({
  queryKey: ['setup-status'],
  staleTime: Infinity,
  gcTime: Infinity,
  queryFn: async () => {
    const response = await setupStatus()
    return response
  },
})
