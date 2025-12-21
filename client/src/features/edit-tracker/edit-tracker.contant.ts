import { EditTrackerOptionEnum } from './edit-tracker.type'
import type { EditTrackerOption } from './edit-tracker.type'

export const HIT_AND_RUN_OPTIONS: Array<EditTrackerOption> = [
  {
    value: EditTrackerOptionEnum.INHERIT,
    label: 'Globál beállítás használata',
  },
  {
    value: EditTrackerOptionEnum.ENABLED,
    label: 'Engedélyezés',
  },
  {
    value: EditTrackerOptionEnum.DISABLED,
    label: 'Letiltás',
  },
]
