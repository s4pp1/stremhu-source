import { TrackerEnum } from 'src/trackers/enum/tracker.enum';

export interface WebTorrentRunToCreate {
  tracker: TrackerEnum;
  torrentId: string;
  infoHash: string;
  imdbId: string;
}
