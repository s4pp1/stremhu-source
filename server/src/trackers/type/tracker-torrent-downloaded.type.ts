import { ParsedTorrent } from 'src/common/utils/parse-torrent.util';

export type TrackerTorrentDownloaded = {
  torrentId: string;
  parsed: ParsedTorrent;
  torrentFilePath: string;
};
