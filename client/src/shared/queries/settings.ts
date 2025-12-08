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
    let downloadLimit: string | null = null
    let uploadLimit: string | null = null

    if (setting.downloadLimit !== -1) {
      downloadLimit = `${setting.downloadLimit / 125_000}`
    }

    if (setting.uploadLimit !== -1) {
      uploadLimit = `${setting.uploadLimit / 125_000}`
    }

    return { ...setting, downloadLimit, uploadLimit }
  },
})

export function useUpdateSetting() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (payload: UpdateSettingDto) => {
      // Letöltési sebesség
      let downloadLimit: number | undefined

      if (payload.downloadLimit !== undefined) {
        downloadLimit = -1

        if (payload.downloadLimit !== -1) {
          downloadLimit = payload.downloadLimit * 125_000
        }
      }

      // Feltöltési sebesség
      let uploadLimit: number | undefined

      if (payload.uploadLimit !== undefined) {
        uploadLimit = -1

        if (payload.uploadLimit !== -1) {
          uploadLimit = payload.uploadLimit * 125_000
        }
      }

      const setting = await appClient.settings.update({
        ...payload,
        downloadLimit,
        uploadLimit,
      })
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
