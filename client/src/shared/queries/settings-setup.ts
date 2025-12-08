import { queryOptions } from '@tanstack/react-query'

import { appClient } from '@/shared/lib/client'

export const getSettingsStatus = queryOptions({
  queryKey: ['setup-status'],
  staleTime: Infinity,
  gcTime: Infinity,
  queryFn: async () => {
    const setupStatus = await appClient.settings.status()
    return setupStatus
  },
})
