import { Readable } from 'node:stream';

export type TorrentClientToAddTorrent = {
  torrentFilePath: string;
  downloadFullTorrent?: boolean;
};

export type TorrentClientToUpdateConfig = {
  downloadLimit?: number;
  uploadLimit?: number;
  connectionsLimit?: number;
  torrentConnectionsLimit?: number;
  enableUpnpAndNatpmp?: boolean;
  port?: number;
};

export type ClientTorrent = {
  infoHash: string;
  name: string;
  downloadSpeed: number;
  uploadSpeed: number;
  downloaded: number;
  uploaded: number;
  progress: number;
  total: number;
};

export type TorrentFileOps = {
  start: number;
  end: number;
};

export type ClientTorrentFile = {
  infoHash: string;
  fileIndex: number;
  name: string;
  total: number;
  createReadStream: (ops: TorrentFileOps) => Promise<Readable> | Readable;
};

export interface TorrentClient {
  bootstrap(): Promise<void>;
  shutdown(): Promise<void>;

  updateConfig(payload: TorrentClientToUpdateConfig): Promise<void> | void;

  getTorrents(): Promise<ClientTorrent[]> | ClientTorrent[];
  getTorrent(infoHash: string): Promise<ClientTorrent | null>;
  addTorrent(payload: TorrentClientToAddTorrent): Promise<ClientTorrent>;
  deleteTorrent(infoHash: string): Promise<ClientTorrent>;
  getTorrentFile(
    infoHash: string,
    fileIndex: number,
  ): Promise<ClientTorrentFile>;
}
