import { TrackerTorrentFile } from 'src/trackers/tracker.types';

import { ParsedStreamIdSeries } from '../pipe/stream-id.pipe';

export type SelectVideoOptions = {
  files: TrackerTorrentFile[];
  series?: ParsedStreamIdSeries;
  isSpecial: boolean;
};
