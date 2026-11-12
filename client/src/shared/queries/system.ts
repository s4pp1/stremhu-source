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
  systemGetStorage,
  systemIndexersCleanup,
  systemRestart,
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

export const getSystemStorage = queryOptions({
  queryKey: ['system', 'storage'],
  refetchInterval: 30_000,
  queryFn: async () => {
    const response = await systemGetStorage()
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
        queryClient.invalidateQueries({ queryKey: getSystemStorage.queryKey }),
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

export function useSystemRestart() {
  return useMutation({
    mutationFn: async () => {
      await systemRestart()
    },
  })
}
