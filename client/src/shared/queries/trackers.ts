import {
  queryOptions,
  useMutation,
  useQueryClient,
} from '@tanstack/react-query'

import { appClient } from '@/shared/lib/client'
import type {
  LoginTrackerDto,
  TrackerEnum,
  UpdateTrackerDto,
} from '@/shared/lib/source-client'

import { getMePreferences } from './me-preferences'
import { getUsers } from './users'

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
      await appClient.trackers.login(payload)
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: getTrackers.queryKey })
    },
  })
}

export function useUpdateTracker(tracker: TrackerEnum) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (payload: UpdateTrackerDto) => {
      await appClient.trackers.update(tracker, payload)
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: getTrackers.queryKey })
    },
  })
}

export function useDeleteTracker() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (tracker: TrackerEnum) => {
      await appClient.trackers.delete(tracker)
    },
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: getTrackers.queryKey }),
        queryClient.invalidateQueries({ queryKey: getMePreferences.queryKey }),
        queryClient.invalidateQueries({ queryKey: getUsers.queryKey }),
      ])
    },
  })
}
