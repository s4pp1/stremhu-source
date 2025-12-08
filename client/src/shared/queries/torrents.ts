import {
  queryOptions,
  useMutation,
  useQueryClient,
} from '@tanstack/react-query'

import { appClient } from '@/shared/lib/client'

export function torrentsOptions() {
  return queryOptions({
    queryKey: ['torrents'],
    refetchInterval: 5000,
    queryFn: async () => {
      const torrents = await appClient.webTorrent.find()

      return torrents
    },
  })
}

export function useDeleteTorrent() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (infoHash: string) => {
      await appClient.webTorrent.delete(infoHash)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['torrents'] })
    },
  })
}
