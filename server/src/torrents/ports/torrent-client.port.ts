import type { WebTorrentTorrent } from 'src/clients/webtorrent/webtorrent.types';
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

  getTorrents(): WebTorrentTorrent[];
  getTorrent(infoHash: string): Promise<WebTorrentTorrent | null>;
  addTorrent(payload: TorrentClientToAddTorrent): Promise<WebTorrentTorrent>;
  deleteTorrent(
    webTorrentTorrent: WebTorrentTorrent,
  ): Promise<WebTorrentTorrent>;
}
