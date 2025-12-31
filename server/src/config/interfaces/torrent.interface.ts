import { TorrentClientEnum } from '../enum/torrent-client.enum';

export interface TorrentConfig {
  client: TorrentClientEnum;
  port: number;
  'downloads-dir': string;
  'torrents-dir': string;
  'peer-limit': number;
  'store-cache-slots': number;
}
