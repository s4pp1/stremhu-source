import { Resolution } from '@ctrl/video-filename-parser';

import { ParsedTorrent } from 'src/common/utils/parse-torrent.util';
import { LanguageEnum } from 'src/preference-items/enum/language.enum';

import { TrackerEnum } from '../enum/tracker.enum';

export const TRACKER_TOKEN = Symbol('TRACKER_TOKEN');

export type AdapterLoginRequest = {
  username: string;
  password: string;
};

export interface AdapterTorrentId {
  tracker: TrackerEnum;
  torrentId: string;
  imdbId: string;
  downloadUrl: string;
}

export interface AdapterTorrent extends AdapterTorrentId {
  language: LanguageEnum;
  resolution: Resolution;
  seeders: number;
}

export interface AdapterParsedTorrent {
  torrentId: string;
  parsed: ParsedTorrent;
}
