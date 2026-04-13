import {
  queryOptions,
  useMutation,
  useQueryClient,
} from '@tanstack/react-query'

import type { UpdateRelaySettingsDto } from '../lib/source/source-client'
import {
  relaySettingsInternalGet,
  relaySettingsInternalUpdate,
} from '../lib/source/source-client'

export const getRelaySettings = queryOptions({
  queryKey: ['relay-settings'],
  queryFn: async () => {
    const settings = await relaySettingsInternalGet()
    return settings
  },
})

export function useUpdateRelaySetting() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (payload: UpdateRelaySettingsDto) => {
      const setting = await relaySettingsInternalUpdate(payload)
      return setting
    },
    onSuccess: async () => {
      await queryClient.fetchQuery({ ...getRelaySettings, staleTime: 0 })
    },
  })
}
