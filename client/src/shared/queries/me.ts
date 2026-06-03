import {
  queryOptions,
  useMutation,
  useQueryClient,
} from '@tanstack/react-query'

import type {
  MePreferenceUpdateRequest,
  MePreferencesReorderRequest,
  MeUpdateRequest,
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
import type { PreferenceDto } from '../type/preference.dto'
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
    mutationFn: async (payload: PreferenceDto) => {
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
    mutationFn: async (payload: MePreferenceUpdateRequest) => {
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
    mutationFn: async (payload: MePreferencesReorderRequest) => {
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
