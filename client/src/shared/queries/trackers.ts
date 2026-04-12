import {
  queryOptions,
  useMutation,
  useQueryClient,
} from '@tanstack/react-query'

import type {
  LoginTrackerDto,
  TrackerEnum,
  UpdateTrackerDto,
} from '../lib/source/source-client'
import {
  trackersDelete,
  trackersLogin,
  trackersTrackers,
  trackersUpdate,
} from '../lib/source/source-client'
import { getMePreferences } from './me-preferences'
import { getUsers } from './users'

export const getTrackers = queryOptions({
  queryKey: ['trackers'],
  queryFn: async () => {
    const trackers = await trackersTrackers()
    return trackers
  },
})

export function useLoginTracker() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (payload: LoginTrackerDto) => {
      await trackersLogin(payload)
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
      await trackersUpdate(tracker, payload)
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
      await trackersDelete(tracker)
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
