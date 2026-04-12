import type { TrackerEnum } from '@/shared/lib/source/source-client'

export type AddTrackerOptions = {
  activeTrackers: TrackerEnum[]
}

export type AddTrackerDialog = {
  type: 'ADD_TRACKER'
  options: AddTrackerOptions
}
