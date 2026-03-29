import { TrackerEnum } from 'src/trackers/enum/tracker.enum';

export type PersistedTorrentToUpdate = {
  tracker?: TrackerEnum;
  torrentId?: string;
  lastPlayedAt?: Date;
  isPersisted?: boolean;
  fullDownload?: boolean | null;
};
