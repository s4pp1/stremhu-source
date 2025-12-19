import {
  queryOptions,
  useMutation,
  useQueryClient,
} from '@tanstack/react-query'

import { appClient } from '@/shared/lib/client'

export const getTorrents = queryOptions({
  queryKey: ['torrents'],
  refetchInterval: 5000,
  queryFn: async () => {
    const torrents = await appClient.torrents.find()

    return torrents
  },
})

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
