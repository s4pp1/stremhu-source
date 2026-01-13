import {
  queryOptions,
  useMutation,
  useQueryClient,
} from '@tanstack/react-query'

import { appClient } from '@/shared/lib/client'
import type { UpdateSettingDto } from '@/shared/lib/source-client'

import { getMetadata } from './metadata'
import { getSettingsStatus } from './settings-setup'

export const getSettings = queryOptions({
  queryKey: ['settings'],
  queryFn: async () => {
    const setting = await appClient.settings.findOne()
    return setting
  },
})

export function useUpdateSetting() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (payload: UpdateSettingDto) => {
      const setting = await appClient.settings.update(payload)
      return setting
    },
    onSuccess: async () => {
      await Promise.all([
        queryClient.fetchQuery({ ...getSettings, staleTime: 0 }),
        queryClient.fetchQuery({ ...getSettingsStatus, staleTime: 0 }),
        queryClient.fetchQuery({ ...getMetadata, staleTime: 0 }),
      ])
    },
  })
}
