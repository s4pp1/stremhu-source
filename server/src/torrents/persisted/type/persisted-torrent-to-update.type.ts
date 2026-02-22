import { TrackerEnum } from 'src/trackers/enum/tracker.enum';

export type PersistedTorrentToUpdate = {
  tracker?: TrackerEnum;
  torrentId?: string;
  uploaded?: number;
  lastPlayedAt?: Date;
  isPersisted?: boolean;
  fullDownload?: boolean | null;
};
