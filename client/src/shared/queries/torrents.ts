import {
  queryOptions,
  useMutation,
  useQueryClient,
} from '@tanstack/react-query'

import { appClient } from '@/shared/lib/client'

import type { UpdateTorrentDto } from '../lib/source-client'

export const getTorrents = queryOptions({
  queryKey: ['torrents'],
  refetchInterval: 5000,
  queryFn: async () => {
    const torrents = await appClient.torrents.find()

    return torrents
  },
})

export function useUpdateTorrent(infoHash: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (payload: UpdateTorrentDto) => {
      await appClient.torrents.update(infoHash, payload)
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
      await appClient.torrents.delete(infoHash)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['torrents'] })
    },
  })
}
