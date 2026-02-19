import { TorrentFileInfo } from './torrent-file-info.type';

export type TorrentInfo = {
  infoHash: string;
  name: string;
  size: number;
  files: TorrentFileInfo[];
};
