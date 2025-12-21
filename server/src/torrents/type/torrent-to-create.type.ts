import { TrackerEnum } from 'src/trackers/enum/tracker.enum';

export type TorrentToCreate = {
  infoHash: string;
  imdbId: string;
  tracker: TrackerEnum;
  torrentId: string;
  lastPlayedAt: Date;
};
