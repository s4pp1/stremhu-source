import {
  queryOptions,
  useMutation,
  useQueryClient,
} from '@tanstack/react-query'

import type { UpdateSettingDto } from '../lib/source/source-client'
import { settingsFindOne, settingsUpdate } from '../lib/source/source-client'
import { getMetadata } from './metadata'
import { getSettingsStatus } from './settings-setup'

export const getSettings = queryOptions({
  queryKey: ['settings'],
  queryFn: async () => {
    const response = await settingsFindOne()
    return response
  },
})

export function useUpdateSetting() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (payload: UpdateSettingDto) => {
      const response = await settingsUpdate(payload)
      return response
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
