import {
  queryOptions,
  useMutation,
  useQueryClient,
} from '@tanstack/react-query'

import { appClient } from '../lib/client'
import type {
  PreferenceEnum,
  ReorderPreferencesDto,
} from '../lib/source-client'
import type { PreferenceDto } from '../type/preference.dto'

export const getUserPreferences = (userId: string) =>
  queryOptions({
    queryKey: ['users', userId, 'preferences'],
    queryFn: async () => {
      const response = await appClient.userPreferences.find(userId)
      return response
    },
  })

export function useCreateUserPreference(userId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (payload: PreferenceDto) => {
      await appClient.userPreferences.create(userId, payload)
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
    queryKey: ['users', userId, preference],
    queryFn: async () => {
      const response = await appClient.userPreferences.findOne(
        userId,
        preference,
      )
      return response
    },
  })

export function useUpdateUserPreference(userId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (payload: PreferenceDto) => {
      await appClient.userPreferences.update(
        userId,
        payload.preference,
        payload,
      )
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
      await appClient.userPreferences.reorder(userId, payload)
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
      await appClient.userPreferences.delete(userId, preference)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ['users', userId, 'preferences'],
      })
    },
  })
}
