import { queryOptions, useMutation } from '@tanstack/react-query'

import { appClient } from '@/shared/lib/client'
import { SourceClient } from '@/shared/lib/source-client'
import { sleep } from '@/shared/lib/utils'

export interface CheckAddressRequest {
  address: string
  enebledlocalIp?: boolean
}

export function getHealth(appUrl: string) {
  return queryOptions({
    queryKey: ['app', 'health', appUrl],
    retry: false,
    queryFn: async () => {
      const customAppClient = new SourceClient({
        BASE: appUrl,
        WITH_CREDENTIALS: true,
      })

      await sleep(1000)

      const request = customAppClient.app.health()
      const timer = setTimeout(() => request.cancel(), 5_000)

      try {
        const response = await request
        return response
      } finally {
        clearTimeout(timer)
      }
    },
  })
}

export function useBuildLocalUrl() {
  return useMutation({
    retry: false,
    mutationFn: async (ipv4: string) => {
      const response = await appClient.settings.buildLocalUrl({
        ipv4,
      })
      return response
    },
  })
}
