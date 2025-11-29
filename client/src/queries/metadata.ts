import { queryOptions } from '@tanstack/react-query'

import { appClient } from '@/client'

export const getMetadata = queryOptions({
  queryKey: ['metadata'],
  staleTime: Infinity,
  gcTime: Infinity,
  queryFn: async () => {
    const metadata = await appClient.metadata.metadata()
    return metadata
  },
})
