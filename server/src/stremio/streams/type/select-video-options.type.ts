import { TrackerTorrentFile } from 'src/trackers/tracker.types';

import { ParsedStremioIdSeries } from '../pipe/stream-id.pipe';

export type SelectVideoOptions = {
  files: TrackerTorrentFile[];
  series?: ParsedStremioIdSeries;
  isSpecial: boolean;
};
