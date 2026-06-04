import {
  queryOptions,
  useMutation,
  useQueryClient,
} from '@tanstack/react-query'

import type {
  MeUpdateRequest,
  PreferenceCreateRequest,
  PreferenceUpdateRequest,
  PreferencesReorderRequest,
} from '../lib/source/source-client'
import {
  meCreatePreference,
  meDeletePreference,
  meGet,
  meGetPreference,
  meGetPreferences,
  meRegenerateApiKey,
  meReorderPreferences,
  meUpdate,
  meUpdatePreference,
} from '../lib/source/source-client'
import { getUsers } from './users'

export function getMe() {
  return queryOptions({
    queryKey: ['me'],
    queryFn: async () => {
      const response = await meGet()
      return response
    },
  })
}

export function useRegenerateApiKey() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async () => {
      const me = await meRegenerateApiKey()
      return me
    },
    onSuccess: (updated) => {
      queryClient.setQueryData(['me'], updated)
      queryClient.invalidateQueries({ queryKey: getUsers.queryKey })
    },
  })
}

export function useUpdateMe() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (payload: MeUpdateRequest) => {
      const me = await meUpdate(payload)
      return me
    },
    onSuccess: (updated) => {
      queryClient.setQueryData(['me'], updated)
      queryClient.invalidateQueries({ queryKey: getUsers.queryKey })
    },
  })
}

export function getMePreferences() {
  return queryOptions({
    queryKey: ['me', 'preferences'],
    queryFn: async () => {
      const response = await meGetPreferences()
      return response
    },
  })
}

export function useCreateMePreference() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (payload: PreferenceCreateRequest) => {
      await meCreatePreference(payload)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['me', 'preferences'] })
    },
  })
}

export function getMePreference(preferenceId: string) {
  return queryOptions({
    queryKey: ['me', 'preferences', preferenceId],
    queryFn: async () => {
      const response = await meGetPreference(preferenceId)
      return response
    },
  })
}

export function useUpdateMePreference(preferenceId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (payload: PreferenceUpdateRequest) => {
      await meUpdatePreference(preferenceId, payload)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['me', 'preferences'] })
    },
  })
}

export function useReorderMePreference() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (payload: PreferencesReorderRequest) => {
      await meReorderPreferences(payload)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['me', 'preferences'] })
    },
  })
}

export function useDeleteMePreference() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (preferenceId: string) => {
      await meDeletePreference(preferenceId)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['me', 'preferences'] })
    },
  })
}
