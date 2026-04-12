import {
  queryOptions,
  useMutation,
  useQueryClient,
} from '@tanstack/react-query'

import type { UpdateRelaySettingsDto } from '../lib/source/source-client'
import {
  torrentsSettings,
  torrentsUpdateSettings,
} from '../lib/source/source-client'

export const getRelaySettings = queryOptions({
  queryKey: ['relay-settings'],
  queryFn: async () => {
    const settings = await torrentsSettings()
    return settings
  },
})

export function useUpdateRelaySetting() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (payload: UpdateRelaySettingsDto) => {
      const setting = await torrentsUpdateSettings(payload)
      return setting
    },
    onSuccess: async () => {
      await queryClient.fetchQuery({ ...getRelaySettings, staleTime: 0 })
    },
  })
}
