import { queryOptions } from '@tanstack/react-query'

import { metadataMetadata } from '../lib/source/source-client'

export const getMetadata = queryOptions({
  queryKey: ['metadata'],
  staleTime: Infinity,
  gcTime: Infinity,
  queryFn: async () => {
    const metadata = await metadataMetadata()
    return metadata
  },
})
