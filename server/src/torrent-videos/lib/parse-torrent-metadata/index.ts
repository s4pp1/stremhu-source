import {
  TorrentMetadataParser,
  TorrentMetadataParserType,
} from './torrent-metadata-parser';

export function parseTorrentMetadata(payload: TorrentMetadataParserType) {
  const torrentMetadataParser = new TorrentMetadataParser(payload);
  return torrentMetadataParser.parse();
}
