import { TrackerEnum } from '../enum/tracker.enum';

export function isTrackerEnum(value: string): value is TrackerEnum {
  return Object.values(TrackerEnum).includes(value as TrackerEnum);
}
