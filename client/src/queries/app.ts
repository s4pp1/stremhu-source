import { queryOptions, useMutation } from '@tanstack/react-query'

import { appClient } from '@/client'
import { AppClient } from '@/client/app-client'
import { sleep } from '@/common/utils'

export interface CheckAddressRequest {
  address: string
  enebledlocalIp?: boolean
}

export function getHealth(appUrl: string) {
  return queryOptions({
    queryKey: ['app', 'health', appUrl],
    retry: false,
    queryFn: async () => {
      const customAppClient = new AppClient({
        BASE: appUrl,
        WITH_CREDENTIALS: true,
      })

      await sleep(1000)

      const response = await customAppClient.app.health()
      return response
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
