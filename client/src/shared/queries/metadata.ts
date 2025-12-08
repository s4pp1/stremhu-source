import { queryOptions } from '@tanstack/react-query'

import { appClient } from '@/shared/lib/client'

export const getMetadata = queryOptions({
  queryKey: ['metadata'],
  staleTime: Infinity,
  gcTime: Infinity,
  queryFn: async () => {
    const metadata = await appClient.metadata.metadata()
    return metadata
  },
})
