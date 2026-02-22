import { TrackerEnum } from 'src/trackers/enum/tracker.enum';

import { StreamIdTypeEnum } from '../enum/stream-id-type.enum';
import { ParsedStreamSeries } from './parsed-stream-series.type';

export type ParsedImdbStreamId = {
  type: StreamIdTypeEnum.IMDB;
  imdbId: string;
  series?: ParsedStreamSeries;
};

export type ParsedTorrentStreamId = {
  type: StreamIdTypeEnum.TORRENT;
  tracker: TrackerEnum;
  torrentId: string;
};

export type ParsedStreamId = ParsedImdbStreamId | ParsedTorrentStreamId;
