import { queryOptions, useMutation } from '@tanstack/react-query'

import {
  monitoringHealth,
  settingsBuildLocalUrl,
} from '@/shared/lib/source/source-client'
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

export function useBuildLocalUrl() {
  return useMutation({
    retry: false,
    mutationFn: async (ipv4: string) => {
      const response = await settingsBuildLocalUrl({
        ipv4,
      })
      return response
    },
  })
}
