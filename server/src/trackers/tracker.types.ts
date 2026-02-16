import { ParsedTorrent } from 'src/common/utils/parse-torrent.util';
import { LanguageEnum } from 'src/preference-items/enum/language.enum';
import { ResolutionEnum } from 'src/preference-items/enum/resolution.enum';
import { StreamMediaTypeEnum } from 'src/stremio/enum/stream-media-type.enum';

import {
  AdapterParsedTorrent,
  AdapterTorrent,
  AdapterTorrentId,
} from './adapters/adapters.types';
import { TrackerEnum } from './enum/tracker.enum';

export interface TrackerTorrentId {
  tracker: TrackerEnum;
  torrentId: string;
  imdbId: string;
  torrentFilePath: string;
}

export interface TrackerTorrentFile {
  name: string;
  size: number;
  fileIndex: number;
}

export interface TrackerTorrent extends TrackerTorrentId {
  name: string;
  infoHash: string;
  files: TrackerTorrentFile[];
  language: LanguageEnum;
  resolution: ResolutionEnum;
  seeders: number;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface TrackerSearchQuery {
  mediaType?: StreamMediaTypeEnum;
  imdbId: string;
}

export interface TrackerAdapter {
  tracker: TrackerEnum;

  login(payload: LoginRequest): Promise<void>;

  find(query: TrackerSearchQuery): Promise<AdapterTorrent[]>;

  findOne(torrentId: string): Promise<AdapterTorrentId>;

  download(payload: AdapterTorrentId): Promise<AdapterParsedTorrent>;

  seedRequirement(): Promise<string[]>;
}

export interface TrackerDownload {
  torrentId: string;
  parsed: ParsedTorrent;
}
