import { queryOptions } from '@tanstack/react-query'

import { monitoringHealth } from '@/shared/lib/source/source-client'
import { sleep } from '@/shared/lib/utils'

export function getHealth(appUrl: string) {
  return queryOptions({
    queryKey: ['app', 'health', appUrl],
    retry: false,
    queryFn: async () => {
      await sleep(1000)

      const response = await monitoringHealth({
        baseURL: appUrl,
        timeout: 5_000,
      })
      return response
    },
  })
}
