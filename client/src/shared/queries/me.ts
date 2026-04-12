import {
  queryOptions,
  useMutation,
  useQueryClient,
} from '@tanstack/react-query'

import type { UpdateMeDto } from '../lib/source/source-client'
import {
  meMe,
  meRegenerateToken,
  meUpdateMe,
} from '../lib/source/source-client'
import { getUsers } from './users'

export const getMe = queryOptions({
  queryKey: ['me'],
  queryFn: async () => {
    const response = await meMe()
    return response.me
  },
})

export function useRegenerateMeToken() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async () => {
      const me = await meRegenerateToken()
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
      const me = await meUpdateMe(payload)
      return me
    },
    onSuccess: (updated) => {
      queryClient.setQueryData(['me'], updated)
      queryClient.invalidateQueries({ queryKey: getUsers.queryKey })
    },
  })
}
