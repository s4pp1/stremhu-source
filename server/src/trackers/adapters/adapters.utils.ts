import { TrackerEnum } from '../enums/tracker.enum';
import { TRACKER_LABEL_MAP } from '../trackers.constants';

export function getTrackerRefreshMessage(tracker: TrackerEnum): string {
  return `🔄 ${TRACKER_LABEL_MAP[tracker]} session frissítése.`;
}

export function getTrackerLoginErrorMessage(tracker: TrackerEnum): string {
  return `Sikertelen bejelentkezés a(z) ${TRACKER_LABEL_MAP[tracker]} fiókba, frissítsd a hitelesítési adatokat!`;
}

export function getTrackerCredentialErrorMessage(tracker: TrackerEnum): string {
  return `${TRACKER_LABEL_MAP[tracker]} hitelesítési információk nincsenek megadva.`;
}

export function getTrackerStructureErrorMessage(tracker: TrackerEnum): string {
  return `${TRACKER_LABEL_MAP[tracker]} nem érhető el vagy megváltozott a strúktúrája.`;
}
