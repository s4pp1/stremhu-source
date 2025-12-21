import { Resolution as ResolutionEnum } from '@ctrl/video-filename-parser';

import { LanguageEnum } from 'src/common/enum/language.enum';
import { ParsedTorrent } from 'src/common/utils/parse-torrent.util';
import { StreamMediaTypeEnum } from 'src/stremio/enum/stream-media-type.enum';

import {
  AdapterParsedTorrent,
  AdapterTorrent,
  AdapterTorrentId,
} from './adapters/adapters.types';
import { TrackerTorrentStatusEnum } from './enum/tracker-torrent-status.enum';
import { TrackerEnum } from './enum/tracker.enum';

export interface TrackerTorrentId {
  tracker: TrackerEnum;
  torrentId: string;
  imdbId: string;
  parsed: ParsedTorrent;
}

export interface TrackerTorrentSuccess extends TrackerTorrentId {
  status: TrackerTorrentStatusEnum.SUCCESS;
  language: LanguageEnum;
  resolution: ResolutionEnum;
  seeders: number;
}

export interface TrackerTorrentError {
  status: TrackerTorrentStatusEnum.ERROR;
  message: string;
}

export type TrackerTorrent = TrackerTorrentSuccess | TrackerTorrentError;

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
