import { MediaTypeEnum } from 'src/common/enum/media-type.enum';
import { LanguageEnum } from 'src/preference-items/enum/language.enum';
import { ResolutionEnum } from 'src/preference-items/enum/resolution.enum';
import { TorrentFileInfo } from 'src/torrents-cache/type/torrent-file-info.type';

import {
  AdapterParsedTorrent,
  AdapterTorrent,
  AdapterTorrentWithInfo,
} from './adapters/adapters.types';
import { TrackerEnum } from './enum/tracker.enum';

export interface TrackerTorrentId {
  tracker: TrackerEnum;
  torrentId: string;
  imdbId: string;
  torrentFilePath: string;
}

export interface TrackerTorrent extends TrackerTorrentId {
  name: string;
  infoHash: string;
  files: TorrentFileInfo[];
  language: LanguageEnum;
  resolution: ResolutionEnum;
  seeders: number;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface TrackerSearchQuery {
  mediaType?: MediaTypeEnum;
  imdbId: string;
}

export interface TrackerAdapter {
  tracker: TrackerEnum;

  login(payload: LoginRequest): Promise<void>;

  find(query: TrackerSearchQuery): Promise<AdapterTorrentWithInfo[]>;

  findOne(torrentId: string): Promise<AdapterTorrent>;

  download(payload: AdapterTorrent): Promise<AdapterParsedTorrent>;

  seedRequirement(): Promise<string[]>;
}

export interface TrackerDownload {
  torrentId: string;
  torrentBuffer: Buffer;
}
