import {
  queryOptions,
  useMutation,
  useQueryClient,
} from '@tanstack/react-query'

import type { TorrentUpdateRequest } from '../lib/source/source-client'
import {
  torrentsDelete,
  torrentsGetList,
  torrentsGetQueue,
  torrentsUpdate,
} from '../lib/source/source-client'

export const getTorrents = queryOptions({
  queryKey: ['torrents'],
  refetchInterval: 1000,
  queryFn: async () => {
    const response = await torrentsGetList()

    return response
  },
})

export const getStorageCleanupQueue = queryOptions({
  queryKey: ['storage-cleanup', 'queue'],
  staleTime: 30_000,
  queryFn: async () => {
    const response = await torrentsGetQueue()

    return response
  },
})

export function useUpdateTorrent(infoHash: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (payload: TorrentUpdateRequest) => {
      await torrentsUpdate(infoHash, payload)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['torrents'] })
      queryClient.invalidateQueries({ queryKey: ['storage-cleanup'] })
    },
  })
}

export function useDeleteTorrent() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (infoHash: string) => {
      await torrentsDelete(infoHash)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['torrents'] })
      queryClient.invalidateQueries({ queryKey: ['storage-cleanup'] })
    },
  })
}
