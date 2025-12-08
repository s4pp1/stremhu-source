import {
  queryOptions,
  useMutation,
  useQueryClient,
} from '@tanstack/react-query'

import { appClient } from '@/shared/lib/client'
import type { LoginTrackerDto, TrackerEnum } from '@/shared/lib/source-client'

export const getTrackers = queryOptions({
  queryKey: ['trackers'],
  queryFn: async () => {
    const trackers = await appClient.trackers.trackers()
    return trackers
  },
})

export function useLoginTracker() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (payload: LoginTrackerDto) => {
      await appClient.trackers.loginTracker(payload)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: getTrackers.queryKey })
    },
  })
}

export function useDeleteTracker() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (tracker: TrackerEnum) => {
      await appClient.trackers.deleteTracker(tracker)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: getTrackers.queryKey })
    },
  })
}
