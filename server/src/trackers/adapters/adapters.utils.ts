import { TrackerEnum } from '../enum/tracker.enum';
import { TRACKER_INFO } from '../trackers.constants';

export function getTrackerRefreshMessage(tracker: TrackerEnum): string {
  return `🔄 ${TRACKER_INFO[tracker].label} session frissítése.`;
}

export function getTrackerLoginErrorMessage(tracker: TrackerEnum): string {
  return `Sikertelen bejelentkezés a(z) ${TRACKER_INFO[tracker].label} fiókba, frissítsd a hitelesítési adatokat!`;
}

export function getTrackerCredentialErrorMessage(tracker: TrackerEnum): string {
  return `${TRACKER_INFO[tracker].label} hitelesítési információk nincsenek megadva.`;
}

export function getTrackerStructureErrorMessage(tracker: TrackerEnum): string {
  return `${TRACKER_INFO[tracker].label} nem érhető el vagy megváltozott a strúktúrája.`;
}
