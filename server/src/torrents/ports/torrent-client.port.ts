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

export type TorrentFileOps = {
  start: number;
  end: number;
};

export type ClientTorrentFile = {
  infoHash: string;
  fileIndex: number;
  name: string;
  total: number;
};
