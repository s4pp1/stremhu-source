import { Resolution } from '@ctrl/video-filename-parser';

import { LanguageEnum } from 'src/common/enums/language.enum';
import { ParsedTorrent } from 'src/common/utils/parse-torrent.util';

import { TrackerEnum } from '../enums/tracker.enum';

export const TRACKER_TOKEN = Symbol('TRACKER_TOKEN');

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
