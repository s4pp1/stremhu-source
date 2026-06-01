import {
  queryOptions,
  useMutation,
  useQueryClient,
} from '@tanstack/react-query'

import type { MeUpdateRequest } from '../lib/source/source-client'
import {
  meGet,
  meRegenerateApiKey,
  meUpdate,
} from '../lib/source/source-client'
import { getUsers } from './users'

export const getMe = queryOptions({
  queryKey: ['me'],
  queryFn: async () => {
    const response = await meGet()
    return response
  },
})

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
