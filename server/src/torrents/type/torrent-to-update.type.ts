import { TrackerEnum } from 'src/trackers/enum/tracker.enum';

export type TorrentToUpdate = {
  imdbId?: string;
  tracker?: TrackerEnum;
  torrentId?: string;
  lastPlayedAt?: Date;
  isPersisted?: boolean;
};
