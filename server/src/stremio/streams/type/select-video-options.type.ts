import { TorrentFileInfo } from 'src/torrents-cache/type/torrent-file-info.type';

import { ParsedStremioIdSeries } from '../pipe/stream-id.pipe';

export type SelectVideoOptions = {
  files: TorrentFileInfo[];
  series?: ParsedStremioIdSeries;
  isSpecial: boolean;
};
