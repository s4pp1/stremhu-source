import {
  queryOptions,
  useMutation,
  useQueryClient,
} from '@tanstack/react-query'

import type {
  NcoreRssFeedUpdate,
  NcoreRssItemUpdate,
  NcoreRssManualItemCreate,
} from '../lib/source/source-client'
import {
  ncoreRssAddManualItem,
  ncoreRssClearFeed,
  ncoreRssConfigureFeed,
  ncoreRssGetItems,
  ncoreRssGetStatus,
  ncoreRssSync,
  ncoreRssUpdateItem,
} from '../lib/source/source-client'

export const getNcoreRssStatus = queryOptions({
  queryKey: ['ncore-rss', 'status'],
  queryFn: async () => ncoreRssGetStatus(),
  refetchInterval: 60_000,
})

export const getNcoreRssItems = queryOptions({
  queryKey: ['ncore-rss', 'items'],
  queryFn: async () => ncoreRssGetItems(),
  refetchInterval: 60_000,
})

function useInvalidateNcoreRss() {
  const queryClient = useQueryClient()
  return async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: getNcoreRssStatus.queryKey }),
      queryClient.invalidateQueries({ queryKey: getNcoreRssItems.queryKey }),
    ])
  }
}

export function useNcoreRssConfigureFeed() {
  const invalidate = useInvalidateNcoreRss()
  return useMutation({
    mutationFn: (payload: NcoreRssFeedUpdate) =>
      ncoreRssConfigureFeed(payload),
    onSuccess: invalidate,
  })
}

export function useNcoreRssClearFeed() {
  const invalidate = useInvalidateNcoreRss()
  return useMutation({
    mutationFn: () => ncoreRssClearFeed(),
    onSuccess: invalidate,
  })
}

export function useNcoreRssSync() {
  const invalidate = useInvalidateNcoreRss()
  return useMutation({
    mutationFn: () => ncoreRssSync(),
    onSuccess: invalidate,
  })
}

export function useNcoreRssAddManualItem() {
  const invalidate = useInvalidateNcoreRss()
  return useMutation({
    mutationFn: (payload: NcoreRssManualItemCreate) =>
      ncoreRssAddManualItem(payload),
    onSuccess: invalidate,
  })
}

export function useNcoreRssUpdateItem() {
  const invalidate = useInvalidateNcoreRss()
  return useMutation({
    mutationFn: ({
      torrentId,
      payload,
    }: {
      torrentId: string
      payload: NcoreRssItemUpdate
    }) => ncoreRssUpdateItem(torrentId, payload),
    onSuccess: invalidate,
  })
}
