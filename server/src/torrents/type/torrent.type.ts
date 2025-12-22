import { TrackerEnum } from 'src/trackers/enum/tracker.enum';

export type MergedTorrent = {
  name: string;
  infoHash: string;
  downloadSpeed: number;
  uploadSpeed: number;
  downloaded: number;
  uploaded: number;
  progress: number;
  total: number;

  imdbId: string;
  tracker: TrackerEnum;
  torrentId: string;
  isPersisted: boolean;

  updatedAt: Date;
  createdAt: Date;
};
