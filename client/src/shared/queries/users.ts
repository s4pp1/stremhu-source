import {
  queryOptions,
  useMutation,
  useQueryClient,
} from '@tanstack/react-query'

import type {
  AttributeExclusionCreateRequest,
  PreferenceCreateRequest,
  PreferenceUpdateRequest,
  PreferencesReorderRequest,
  UserCreateRequest,
  UserUpdateRequest,
} from '@/shared/lib/source/source-client'
import {
  usersCreate,
  usersCreateAttributeExclusion,
  usersCreatePreferenceDefinition,
  usersDelete,
  usersDeleteAttributeExclusion,
  usersDeletePreferenceDefinition,
  usersGet,
  usersGetAttributeExclusions,
  usersGetAttributes,
  usersGetList,
  usersGetPreference,
  usersGetPreferenceDefinition,
  usersGetPreferenceDefinitions,
  usersGetPreferences,
  usersRegenerateApiKey,
  usersReorderPreferenceDefinitions,
  usersUpdate,
  usersUpdatePreferenceDefinition,
} from '@/shared/lib/source/source-client'

import { getMe } from './me'

export const getUsers = queryOptions({
  queryKey: ['users'],
  queryFn: async () => {
    const users = await usersGetList()
    return users
  },
})

export const getUser = (userId: string) =>
  queryOptions({
    queryKey: ['users', userId],
    queryFn: async () => {
      const user = await usersGet(userId)
      return user
    },
  })

export function useAddUser() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (payload: UserCreateRequest) => {
      const user = await usersCreate(payload)
      return user
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: getUsers.queryKey })
    },
  })
}

export function useUserDelete() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (userId: string) => {
      await usersDelete(userId)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: getUsers.queryKey })
    },
  })
}

export function useRegenerateUserToken() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (userId: string) => {
      const user = await usersRegenerateApiKey(userId)
      return user
    },
    onSuccess: (updated) => {
      queryClient.invalidateQueries({ queryKey: getUsers.queryKey })
      queryClient.setQueryData(getMe().queryKey, (prev) => {
        if (!prev) return prev
        const isSelf = prev.id === updated.id
        return isSelf ? updated : prev
      })
    },
  })
}

export function useUserUpdate() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (data: {
      userId: string
      payload: UserUpdateRequest
    }) => {
      const { userId, payload } = data
      const user = await usersUpdate(userId, payload)
      return user
    },
    onSuccess: (updated, { userId, payload }) => {
      const me = queryClient.getQueryData(getMe().queryKey)
      if (payload.password !== undefined && me?.id === userId) {
        queryClient.clear()
        return
      }
      queryClient.invalidateQueries({ queryKey: getUsers.queryKey })
      queryClient.setQueryData(getMe().queryKey, (prev) => {
        if (!prev) return prev
        const isSelf = prev.id === updated.id
        return isSelf ? updated : prev
      })
    },
  })
}

// User Attributes

export function getUserAttributes(userId: string) {
  return queryOptions({
    queryKey: ['users', userId, 'attributes'],
    queryFn: async () => {
      const response = await usersGetAttributes(userId)
      return response
    },
  })
}

// Me Attribute Exclusions

export const getUserAttributeExclusions = (userId: string) =>
  queryOptions({
    queryKey: ['users', userId, 'attributes', 'exclusions'],
    queryFn: async () => {
      const response = await usersGetAttributeExclusions(userId)
      return response
    },
  })

export function useUserAddAttributeToExclusion(userId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (payload: AttributeExclusionCreateRequest) => {
      await usersCreateAttributeExclusion(userId, payload)
    },
    onSuccess: async () => {
      await Promise.all(
        [
          ['users', userId, 'attributes'],
          ['users', userId, 'preferences'],
        ].map((queryKey) => queryClient.invalidateQueries({ queryKey })),
      )
    },
  })
}

export function useUserRemoveAttributeFromExclusion(userId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (attributeId: string) => {
      await usersDeleteAttributeExclusion(userId, attributeId)
    },
    onSuccess: async () => {
      await Promise.all(
        [
          ['users', userId, 'attributes'],
          ['users', userId, 'preferences'],
        ].map((queryKey) => queryClient.invalidateQueries({ queryKey })),
      )
    },
  })
}

// User Preferences

export const getUserPreferences = (userId: string) =>
  queryOptions({
    queryKey: ['users', userId, 'preferences'],
    queryFn: async () => {
      const response = await usersGetPreferences(userId)
      return response
    },
  })

export const getUserPreference = (userId: string, preferenceId: string) =>
  queryOptions({
    queryKey: ['users', userId, 'preferences', preferenceId],
    queryFn: async () => {
      const response = await usersGetPreference(userId, preferenceId)
      return response
    },
  })

// User Preference Definitions

export const getUserPreferenceDefinitions = (userId: string) =>
  queryOptions({
    queryKey: ['users', userId, 'preferences', 'definitions'],
    queryFn: async () => {
      const response = await usersGetPreferenceDefinitions(userId)
      return response
    },
  })

export function useCreateUserPreferenceDefinition(userId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (payload: PreferenceCreateRequest) => {
      await usersCreatePreferenceDefinition(userId, payload)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ['users', userId, 'preferences', 'definitions'],
      })
    },
  })
}

export const getUserPreferenceDefinition = (
  userId: string,
  preference_id: string,
) =>
  queryOptions({
    queryKey: ['users', userId, 'preferences', 'definitions', preference_id],
    queryFn: async () => {
      const response = await usersGetPreferenceDefinition(userId, preference_id)
      return response
    },
  })

export function useUpdateUserPreference(userId: string, preference_id: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (payload: PreferenceUpdateRequest) => {
      await usersUpdatePreferenceDefinition(userId, preference_id, payload)
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
    mutationFn: async (payload: PreferencesReorderRequest) => {
      await usersReorderPreferenceDefinitions(userId, payload)
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
    mutationFn: async (preference_id: string) => {
      await usersDeletePreferenceDefinition(userId, preference_id)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ['users', userId, 'preferences'],
      })
    },
  })
}
