import { TorrentClientEnum } from '../enum/torrent-client.enum';

export interface TorrentConfig {
  client: TorrentClientEnum;
  port: number;
  'torrents-dir': string;
  'relay-auto-start': boolean;
}
