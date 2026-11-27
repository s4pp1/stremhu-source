import {
  queryOptions,
  useMutation,
  useQueryClient,
} from '@tanstack/react-query'

import type {
  IndexerCredentialsUpdateRequest,
  IndexerLoginRequest,
  IndexerUpdateRequest,
} from '../lib/source/source-client'
import {
  indexersDelete,
  indexersGetDefinitionList,
  indexersGetList,
  indexersLogin,
  indexersUpdate,
  indexersUpdateCredentials,
} from '../lib/source/source-client'
import { getMePreferences } from './me'
import { getPreferences } from './preferences'
import { getUsers } from './users'

export const getIndexers = queryOptions({
  queryKey: ['indexers'],
  queryFn: async () => {
    const indexers = await indexersGetList()
    return indexers
  },
})

export const getIndexerDefinitions = queryOptions({
  queryKey: ['indexer-definitions'],
  queryFn: async () => {
    const indexers = await indexersGetDefinitionList()
    return indexers
  },
})

export function useIndexerLogin() {
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

export function useIndexerUpdate(indexerId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (payload: IndexerUpdateRequest) => {
      await indexersUpdate(indexerId, payload)
    },
    onSuccess: async () => {
      await Promise.all(
        [
          getIndexers.queryKey,
          getMePreferences().queryKey,
          getPreferences.queryKey,
        ].map((queryKey) => queryClient.invalidateQueries({ queryKey })),
      )
    },
  })
}

export function useIndexerUpdateCredentials(indexerId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (payload: IndexerCredentialsUpdateRequest) => {
      await indexersUpdateCredentials(indexerId, payload)
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: getIndexers.queryKey })
    },
  })
}

export function useIndexerDelete() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (indexerId: string) => {
      await indexersDelete(indexerId)
    },
    onSuccess: async () => {
      await Promise.all(
        [
          getIndexers.queryKey,
          getMePreferences().queryKey,
          getPreferences.queryKey,
          getUsers.queryKey,
        ].map((queryKey) => queryClient.invalidateQueries({ queryKey })),
      )
    },
  })
}
