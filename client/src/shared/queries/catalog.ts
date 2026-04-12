import { queryOptions } from '@tanstack/react-query'

import { sleep } from '@/shared/lib/utils'

import { catalogHealth } from '../lib/source/source-client'

export const getCatalogHealth = queryOptions({
  queryKey: ['catalog', 'health'],
  retry: false,
  queryFn: async () => {
    await sleep(1000)

    const response = await catalogHealth({
      timeout: 5_000,
    })
    return response
  },
})
