import {
  queryOptions,
  useMutation,
  useQueryClient,
} from '@tanstack/react-query'

import type { UpdateTorrentDto } from '../lib/source/source-client'
import {
  torrentsDelete,
  torrentsFind,
  torrentsUpdate,
} from '../lib/source/source-client'

export const getTorrents = queryOptions({
  queryKey: ['torrents'],
  refetchInterval: 5000,
  queryFn: async () => {
    const response = await torrentsFind()

    return response
  },
})

export function useUpdateTorrent(infoHash: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (payload: UpdateTorrentDto) => {
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
