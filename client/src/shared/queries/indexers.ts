import {
  queryOptions,
  useMutation,
  useQueryClient,
} from '@tanstack/react-query'

import type {
  IndexerLoginRequest,
  IndexerUpdateRequest,
} from '../lib/source/source-client'
import {
  indexersDelete,
  indexersGetList,
  indexersLogin,
  indexersUpdate,
} from '../lib/source/source-client'
import { getMePreferences } from './me'
import { getUsers } from './users'

export const getIndexers = queryOptions({
  queryKey: ['indexers'],
  queryFn: async () => {
    const indexers = await indexersGetList()
    return indexers
  },
})

export function useLoginTracker() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (payload: IndexerLoginRequest) => {
      await indexersLogin(payload)
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: getIndexers.queryKey })
    },
  })
}

export function useUpdateIndexer(indexerId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (payload: IndexerUpdateRequest) => {
      await indexersUpdate(indexerId, payload)
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: getIndexers.queryKey })
    },
  })
}

export function useDeleteIndexer() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (indexerId: string) => {
      await indexersDelete(indexerId)
    },
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: getIndexers.queryKey }),
        queryClient.invalidateQueries({
          queryKey: getMePreferences().queryKey,
        }),
        queryClient.invalidateQueries({ queryKey: getUsers.queryKey }),
      ])
    },
  })
}
