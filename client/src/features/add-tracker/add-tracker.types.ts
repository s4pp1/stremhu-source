import type { TrackerEnum } from '@/shared/lib/source-client'

export type AddTrackerOptions = {
  activeTrackers: Array<TrackerEnum>
}

export type AddTrackerDialog = {
  type: 'ADD_TRACKER'
  options: AddTrackerOptions
}
