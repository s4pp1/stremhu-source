import { Resolution } from '@ctrl/video-filename-parser';

import { LanguageEnum } from 'src/common/enums/language.enum';
import { ParsedTorrent } from 'src/common/utils/parse-torrent.util';
import { StreamMediaTypeEnum } from 'src/stremio/enums/stream-media-type.enum';

import {
  AdapterParsedTorrent,
  AdapterTorrent,
  AdapterTorrentId,
} from './adapters/adapters.types';
import { TrackerEnum } from './enums/tracker.enum';

export interface TrackerOption {
  value: TrackerEnum;
  label: string;
}

export interface TrackerTorrentId {
  tracker: TrackerEnum;
  torrentId: string;
  imdbId: string;
  parsed: ParsedTorrent;
}

export interface TrackerTorrent extends TrackerTorrentId {
  language: LanguageEnum;
  resolution: Resolution;
  seeders: number;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface TrackerSearchQuery {
  mediaType: StreamMediaTypeEnum;
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
