import { TrackerEnum } from '../enums/tracker.enum';
import { TRACKER_LABEL_MAP } from '../trackers.constants';

export function getTrackerRefreshMessage(tracker: TrackerEnum) {
  return `🔄 ${TRACKER_LABEL_MAP[tracker]} session frissítése`;
}

export function getTrackerLoginErrorMessage(tracker: TrackerEnum) {
  return `Sikertelen bejelentkezés a(z) ${TRACKER_LABEL_MAP[tracker]} fiókba, ellenőrizd az oldalt vagy frissítsd a hitelesítési adatokat!`;
}

export function getTrackerCredentialErrorMessage(tracker: TrackerEnum) {
  return `${TRACKER_LABEL_MAP[tracker]} hitelesítési információk nincsenek megadva`;
}
