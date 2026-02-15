import { TRACKER_LABEL } from '../constant/trackers-label.constant';
import { TrackerEnum } from '../enum/tracker.enum';

export function getTrackerRefreshMessage(tracker: TrackerEnum): string {
  return `🔄 ${TRACKER_LABEL[tracker]} session frissítése.`;
}

export function getTrackerLoginErrorMessage(tracker: TrackerEnum): string {
  return `Sikertelen bejelentkezés a(z) ${TRACKER_LABEL[tracker]} fiókba.`;
}

export function getTrackerCredentialErrorMessage(tracker: TrackerEnum): string {
  return `${TRACKER_LABEL[tracker]} hitelesítési információk nincsenek megadva.`;
}

export function getTrackerStructureErrorMessage(tracker: TrackerEnum): string {
  return `${TRACKER_LABEL[tracker]} nem érhető el vagy megváltozott a strúktúrája.`;
}

export function getTrackerTorrentDownloadErrorMessage(
  tracker: TrackerEnum,
  torrentId: string,
): string {
  return `🚨 Hiba történt a(z) "[${TRACKER_LABEL[tracker]}] - ${torrentId}" torrent letöltése közben.`;
}
