import {
  queryOptions,
  useMutation,
  useQueryClient,
} from '@tanstack/react-query'

import type {
  PreferenceEnum,
  ReorderPreferencesDto,
} from '../lib/source/source-client'
import {
  userPreferencesCreate,
  userPreferencesDelete,
  userPreferencesFind,
  userPreferencesFindOne,
  userPreferencesReorder,
  userPreferencesUpdate,
} from '../lib/source/source-client'
import type { PreferenceDto } from '../type/preference.dto'

export const getUserPreferences = (userId: string) =>
  queryOptions({
    queryKey: ['users', userId, 'preferences'],
    queryFn: async () => {
      const response = await userPreferencesFind(userId)
      return response
    },
  })

export function useCreateUserPreference(userId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (payload: PreferenceDto) => {
      await userPreferencesCreate(userId, payload)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ['users', userId, 'preferences'],
      })
    },
  })
}

export const getUserPreference = (userId: string, preference: PreferenceEnum) =>
  queryOptions({
    queryKey: ['users', userId, 'preferences', preference],
    queryFn: async () => {
      const response = await userPreferencesFindOne(userId, preference)
      return response
    },
  })

export function useUpdateUserPreference(userId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (payload: PreferenceDto) => {
      await userPreferencesUpdate(userId, payload.preference, payload)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ['users', userId, 'preferences'],
      })
    },
  })
}

export function useReorderUserPreference(userId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (payload: ReorderPreferencesDto) => {
      await userPreferencesReorder(userId, payload)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ['users', userId, 'preferences'],
      })
    },
  })
}

export function useDeleteUserPreference(userId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (preference: PreferenceEnum) => {
      await userPreferencesDelete(userId, preference)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ['users', userId, 'preferences'],
      })
    },
  })
}
