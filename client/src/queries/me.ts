import {
  queryOptions,
  useMutation,
  useQueryClient,
} from '@tanstack/react-query'

import { appClient } from '@/client'
import type {
  ChangePasswordDto,
  ChangeUsernameDto,
  UpdateMePreferencesDto,
} from '@/client/app-client'

import { getUsers } from './users'

export const getMe = queryOptions({
  queryKey: ['me'],
  queryFn: async () => {
    const response = await appClient.me.usersMeControllerMe()
    return response.me
  },
})

export function useChangeMeUsername() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (payload: ChangeUsernameDto) => {
      const me = await appClient.me.usersMeControllerChangeUsername(payload)
      return me
    },
    onSuccess: (updated) => {
      queryClient.setQueryData(['me'], updated)
      queryClient.invalidateQueries({ queryKey: getUsers.queryKey })
    },
  })
}

export function useChangeMePassword() {
  return useMutation({
    mutationFn: async (payload: ChangePasswordDto) => {
      const me = await appClient.me.usersMeControllerChangePassword(payload)
      return me
    },
  })
}

export function useChangeMeStremioToken() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async () => {
      const me = await appClient.me.usersMeControllerChangeStremioToken()
      return me
    },
    onSuccess: (updated) => {
      queryClient.setQueryData(['me'], updated)
      queryClient.invalidateQueries({ queryKey: getUsers.queryKey })
    },
  })
}

export function useUpdateMePreferences() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (payload: UpdateMePreferencesDto) => {
      const me = await appClient.me.usersMeControllerUpdateMe(payload)
      return me
    },
    onSuccess: (updated) => {
      queryClient.setQueryData(['me'], updated)
      queryClient.invalidateQueries({ queryKey: getUsers.queryKey })
    },
  })
}
