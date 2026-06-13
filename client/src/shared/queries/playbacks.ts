import { queryOptions } from '@tanstack/react-query'

import type { PlaybacksGetHistoryListParams } from '../lib/source/source-client'
import {
  playbacksGetHistoryList,
  playbacksGetList,
} from '../lib/source/source-client'

export const getPlaybacks = queryOptions({
  queryKey: ['playbacks'],
  refetchInterval: 1000,
  queryFn: async () => {
    const response = await playbacksGetList()
    return response
  },
})

export const getPlaybackHistories = (
  query: PlaybacksGetHistoryListParams = {},
) =>
  queryOptions({
    queryKey: ['playbacks', 'histories', query],
    refetchInterval: 5000,
    queryFn: async () => {
      const response = await playbacksGetHistoryList(query)
      return response
    },
  })
