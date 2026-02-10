import { TrackerEnum } from 'src/trackers/enum/tracker.enum';

export type PersistedTorrentToCreate = {
  infoHash: string;
  imdbId: string;
  tracker: TrackerEnum;
  torrentId: string;
};
