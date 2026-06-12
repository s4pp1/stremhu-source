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
  meCreatePreferenceDefinition,
  meDeletePreferenceDefinition,
  meGet,
  meGetAttributeExclusions,
  meGetAttributes,
  meGetPreference,
  meGetPreferenceDefinition,
  meGetPreferenceDefinitions,
  meGetPreferences,
  meRegenerateApiKey,
  meReorderPreferenceDefinitions,
  meUpdate,
  meUpdatePreferenceDefinition,
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

// Me Attributes

export function getMeAttributes() {
  return queryOptions({
    queryKey: ['me', 'attributes'],
    queryFn: async () => {
      const response = await meGetAttributes()
      return response
    },
  })
}

// Me Attribute Exclusions

export function getMeAttributeExclusions() {
  return queryOptions({
    queryKey: ['me', 'attributes', 'exclusions'],
    queryFn: async () => {
      const response = await meGetAttributeExclusions()
      return response
    },
  })
}

// Me Preferences

export function getMePreferences() {
  return queryOptions({
    queryKey: ['me', 'preferences'],
    queryFn: async () => {
      const response = await meGetPreferences()
      return response
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

// Me Preference Definitions

export function getMePreferenceDefinitions() {
  return queryOptions({
    queryKey: ['me', 'preferences', 'definitions'],
    queryFn: async () => {
      const response = await meGetPreferenceDefinitions()
      return response
    },
  })
}

export function useCreateMePreference() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (payload: PreferenceCreateRequest) => {
      await meCreatePreferenceDefinition(payload)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['me', 'preferences'] })
    },
  })
}

export function getMePreferenceDefinition(preferenceId: string) {
  return queryOptions({
    queryKey: ['me', 'preferences', 'definitions', preferenceId],
    queryFn: async () => {
      const response = await meGetPreferenceDefinition(preferenceId)
      return response
    },
  })
}

export function useUpdateMePreference(preferenceId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (payload: PreferenceUpdateRequest) => {
      await meUpdatePreferenceDefinition(preferenceId, payload)
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
      await meReorderPreferenceDefinitions(payload)
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
      await meDeletePreferenceDefinition(preferenceId)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['me', 'preferences'] })
    },
  })
}
