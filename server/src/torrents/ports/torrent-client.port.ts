import type { WebTorrentTorrent as ClientTorrent } from 'src/clients/webtorrent/webtorrent.types';

import { ParsedTorrent } from 'src/common/utils/parse-torrent.util';

export interface TorrentClientToAddTorrent {
  parsedTorrent: ParsedTorrent;
  downloadFullTorrent?: boolean;
}

export interface TorrentClientToUpdateConfig {
  downloadLimit: number;
  uploadLimit: number;
}

export interface TorrentClient {
  bootstrap(): Promise<void>;
  shutdown(): Promise<void>;

  updateConfig(payload: TorrentClientToUpdateConfig): void;

  getTorrents(): ClientTorrent[];
  getTorrent(infoHash: string): Promise<ClientTorrent>;
  addTorrent(payload: TorrentClientToAddTorrent): Promise<ClientTorrent>;
  deleteTorrent(infoHash: string): Promise<ClientTorrent>;
}

