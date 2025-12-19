import {
  queryOptions,
  useMutation,
  useQueryClient,
} from '@tanstack/react-query'

import { appClient } from '@/shared/lib/client'

import type { UpdateMeDto } from '../lib/source-client'
import { getUsers } from './users'

export const getMe = queryOptions({
  queryKey: ['me'],
  queryFn: async () => {
    const response = await appClient.me.me()
    return response.me
  },
})

export function useRegenerateMeToken() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async () => {
      const me = await appClient.me.regenerateToken()
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
    mutationFn: async (payload: UpdateMeDto) => {
      const me = await appClient.me.updateMe(payload)
      return me
    },
    onSuccess: (updated) => {
      queryClient.setQueryData(['me'], updated)
      queryClient.invalidateQueries({ queryKey: getUsers.queryKey })
    },
  })
}
