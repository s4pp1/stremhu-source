import { queryOptions } from '@tanstack/react-query'

import { appClient } from '@/shared/lib/client'
import { sleep } from '@/shared/lib/utils'

export const getCatalogHealth = queryOptions({
  queryKey: ['catalog', 'health'],
  retry: false,
  queryFn: async () => {
    await sleep(1000)

    const request = appClient.stremHuCatalog.health()
    const timer = setTimeout(() => request.cancel(), 5_000)

    try {
      const response = await request
      return response
    } finally {
      clearTimeout(timer)
    }
  },
})
