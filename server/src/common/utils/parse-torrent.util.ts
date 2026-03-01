import { files, hash, info } from '@ctrl/torrent-file';
import { Logger } from '@nestjs/common';

import { TorrentFileInfo } from 'src/torrents-cache/type/torrent-file-info.type';
import { TorrentInfo } from 'src/torrents-cache/type/torrent-info.type';

const logger = new Logger('ParseTorrentUtil');

export function parseTorrent(buffer: Buffer): TorrentInfo | null {
  try {
    return parseTorrentOrThrow(buffer);
  } catch (error) {
    logger.error(
      `🚨 Nem sikerült feldolgozni a torrent tartalmát: érvénytelen vagy sérült .torrent adat.`,
      error,
    );
    return null;
  }
}

export function parseTorrentOrThrow(buffer: Buffer): TorrentInfo {
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
