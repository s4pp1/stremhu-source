import {
  queryOptions,
  useMutation,
  useQueryClient,
} from '@tanstack/react-query'

import type {
  UserCreateRequest,
  UserUpdateRequest,
} from '@/shared/lib/source/source-client'
import {
  usersCreate,
  usersDelete,
  usersGet,
  usersGetList,
  usersRegenerateApiKey,
  usersUpdate,
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

export function useDeleteUser() {
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

export function useUpdateUser() {
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
