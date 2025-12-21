import type { TrackerDto } from '@/shared/lib/source-client'

export type EditTrackerOptions = {
  tracker: TrackerDto
}

export type EditTrackerDialog = {
  type: 'EDIT_TRACKER'
  options: EditTrackerOptions
}

export enum EditTrackerOptionEnum {
  INHERIT = 'inherit',
  ENABLED = 'enabled',
  DISABLED = 'disabled',
}

export type EditTrackerOption = {
  value: EditTrackerOptionEnum
  label: string
}
