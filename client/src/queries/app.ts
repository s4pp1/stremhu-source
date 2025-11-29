import { useMutation } from '@tanstack/react-query'

import { appClient } from '@/client'
import { AppClient } from '@/client/app-client'

export interface CheckAddressRequest {
  address: string
  enebledlocalIp: boolean
}

let inflightAppHealth: ReturnType<AppClient['app']['health']> | null = null

export function useCheckAddress() {
  return useMutation({
    mutationFn: async (payload: CheckAddressRequest) => {
      inflightAppHealth?.cancel()

      let appUrl = payload.address

      if (payload.enebledlocalIp) {
        const { localUrl } = await appClient.settings.buildLocalUrl({
          ipv4: payload.address,
        })
        appUrl = localUrl
      }

      const customAppClient = new AppClient({
        BASE: appUrl,
        WITH_CREDENTIALS: true,
      })

      inflightAppHealth = customAppClient.app.health()

      const response = await inflightAppHealth
      return response
    },
  })
}
