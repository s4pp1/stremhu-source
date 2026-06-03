import {
  queryOptions,
  useMutation,
  useQueryClient,
} from '@tanstack/react-query'

import type { TorrentUpdateRequest } from '../lib/source/source-client'
import {
  torrentsDelete,
  torrentsGetList,
  torrentsUpdate,
} from '../lib/source/source-client'

export const getTorrents = queryOptions({
  queryKey: ['torrents'],
  refetchInterval: 5000,
  queryFn: async () => {
    const response = await torrentsGetList()

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
    },
  })
}
