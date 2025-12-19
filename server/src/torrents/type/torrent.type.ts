import { TrackerEnum } from 'src/trackers/enum/tracker.enum';

export type MergedTorrent = {
  name: string;
  infoHash: string;
  downloaded: number;
  progress: number;
  total: number;
  uploaded: number;
  uploadSpeed: number;

  imdbId: string;
  tracker: TrackerEnum;
  torrentId: string;

  updatedAt: Date;
  createdAt: Date;
};
