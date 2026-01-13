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

    let downloadLimit = null
    if (settings.downloadLimit !== 0) {
      downloadLimit = `${settings.downloadLimit / 125_000}`
    }

    let uploadLimit = null
    if (settings.uploadLimit !== 0) {
      uploadLimit = `${settings.uploadLimit / 125_000}`
    }

    return { ...settings, downloadLimit, uploadLimit }
  },
})

export function useUpdateRelaySetting() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (payload: UpdateRelaySettingsDto) => {
      // Letöltési sebesség
      let downloadLimit: number | undefined

      if (payload.downloadLimit !== undefined) {
        downloadLimit = payload.downloadLimit * 125_000
      }

      // Feltöltési sebesség
      let uploadLimit: number | undefined

      if (payload.uploadLimit !== undefined) {
        uploadLimit = payload.uploadLimit * 125_000
      }

      const setting = await appClient.torrents.updateSettings({
        ...payload,
        downloadLimit,
        uploadLimit,
      })
      return setting
    },
    onSuccess: async () => {
      await queryClient.fetchQuery({ ...getRelaySettings, staleTime: 0 })
    },
  })
}
