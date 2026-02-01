import {
  queryOptions,
  useMutation,
  useQueryClient,
} from '@tanstack/react-query'

import { appClient } from '../lib/client'
import type { UpdateRelaySettingsDto } from '../lib/source-client'

export const getRelaySettings = queryOptions({
  queryKey: ['relay-settings'],
  queryFn: async () => {
    const settings = await appClient.torrents.settings()
    return settings
  },
})

export function useUpdateRelaySetting() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (payload: UpdateRelaySettingsDto) => {
      const setting = await appClient.torrents.updateSettings(payload)
      return setting
    },
    onSuccess: async () => {
      await queryClient.fetchQuery({ ...getRelaySettings, staleTime: 0 })
    },
  })
}
