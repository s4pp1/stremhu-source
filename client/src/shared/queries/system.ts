import {
  queryOptions,
  useMutation,
  useQueryClient,
} from '@tanstack/react-query'

import type { SystemSettingsUpdateRequest } from '../lib/source/source-client'
import {
  systemGetRoles,
  systemGetSettings,
  systemGetStatus,
  systemIndexersCleanup,
  systemTorrentFilesCleanup,
  systemUpdateSettings,
} from '../lib/source/source-client'

export const getSystemStatus = queryOptions({
  queryKey: ['system', 'status'],
  staleTime: Infinity,
  gcTime: Infinity,
  queryFn: async () => {
    const response = await systemGetStatus()
    return response
  },
})

export const getSystemRoles = queryOptions({
  queryKey: ['system', 'roles'],
  queryFn: async () => {
    const response = await systemGetRoles()
    return response
  },
})

export const getSystemSettings = queryOptions({
  queryKey: ['system', 'settings'],

  queryFn: async () => {
    const response = await systemGetSettings()
    return response
  },
})

export function useSystemSettingsUpdate() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (payload: SystemSettingsUpdateRequest) => {
      const response = await systemUpdateSettings(payload)
      return response
    },
    onSuccess: async () => {
      await Promise.all([
        queryClient.fetchQuery({ ...getSystemSettings, staleTime: 0 }),
        queryClient.fetchQuery({ ...getSystemStatus, staleTime: 0 }),
      ])
    },
  })
}

export function useSystemTorrentFilesCleanup() {
  return useMutation({
    mutationFn: async () => {
      await systemTorrentFilesCleanup()
    },
  })
}

export function useSystemIndexersCleanup() {
  return useMutation({
    mutationFn: async () => {
      await systemIndexersCleanup()
    },
  })
}
