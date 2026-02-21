import { TorrentFileInfo } from 'src/torrents-cache/type/torrent-file-info.type';

import { ParsedStreamSeries } from './parsed-stream-series.type';

export type SelectVideoOptions = {
  files: TorrentFileInfo[];
  series?: ParsedStreamSeries;
  isSpecial: boolean;
};
