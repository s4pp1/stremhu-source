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
  refetchIntervalInBackground: false,
  refetchInterval: (query) => {
    const list = query.state.data
    // M15: Adaptív lekérdezés: aktív letöltésnél sűrűbb (1.5s), nyugalmi állapotban kímélő (5s)
    const hasActive = list?.some(
      (t) => t.downloadSpeed > 0 || (t.total > 0 && t.downloaded < t.total),
    )
    return hasActive ? 1500 : 5000
  },
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
