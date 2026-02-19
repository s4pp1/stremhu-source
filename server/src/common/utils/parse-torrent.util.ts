import { files, hash, info } from '@ctrl/torrent-file';

import { TorrentFileInfo } from 'src/torrents-cache/type/torrent-file-info.type';
import { TorrentInfo } from 'src/torrents-cache/type/torrent-info.type';

export function parseTorrent(buffer: Buffer): TorrentInfo {
  const infoHash = hash(buffer);
  const torrentInfo = info(buffer);
  const fileInfo = files(buffer);

  const torrentFiles: TorrentFileInfo[] = fileInfo.files.map((file, index) => ({
    index,
    name: file.name,
    size: file.length,
  }));

  return {
    infoHash,
    name: torrentInfo.name,
    size: fileInfo.length,
    files: torrentFiles,
  };
}
