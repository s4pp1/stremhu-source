import {
  queryOptions,
  useMutation,
  useQueryClient,
} from '@tanstack/react-query'

import { appClient } from '@/shared/lib/client'
import type { CreateUserDto, UpdateUserDto } from '@/shared/lib/source-client'

import { getMe } from './me'

export const getUsers = queryOptions({
  queryKey: ['users'],
  queryFn: async () => {
    const users = await appClient.users.find()
    return users
  },
})

export const getUser = (userId: string) =>
  queryOptions({
    queryKey: ['users', userId],
    queryFn: async () => {
      const user = await appClient.users.findOne(userId)
      return user
    },
  })

export function useAddUser() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (payload: CreateUserDto) => {
      const user = await appClient.users.create(payload)
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
      await appClient.users.deleteOne(userId)
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
      const user = await appClient.users.regenerateToken(userId)
      return user
    },
    onSuccess: (updated) => {
      queryClient.invalidateQueries({ queryKey: getUsers.queryKey })
      queryClient.setQueryData(getMe.queryKey, (prev) => {
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
    mutationFn: async (data: { userId: string; payload: UpdateUserDto }) => {
      const { userId, payload } = data
      const user = await appClient.users.updateOne(userId, payload)
      return user
    },
    onSuccess: (updated) => {
      queryClient.invalidateQueries({ queryKey: getUsers.queryKey })
      queryClient.setQueryData(getMe.queryKey, (prev) => {
        if (!prev) return prev
        const isSelf = prev.id === updated.id
        return isSelf ? updated : prev
      })
    },
  })
}
