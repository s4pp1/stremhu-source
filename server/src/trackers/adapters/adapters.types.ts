import { LanguageEnum } from 'src/preference-items/enum/language.enum';
import { ResolutionEnum } from 'src/preference-items/enum/resolution.enum';

import { TrackerEnum } from '../enum/tracker.enum';

export const TRACKER_TOKEN = Symbol('TRACKER_TOKEN');

export type AdapterLoginRequest = {
  username: string;
  password: string;
};

export interface AdapterTorrent {
  tracker: TrackerEnum;
  torrentId: string;
  downloadUrl: string;
  imdbId?: string;
}

export interface AdapterTorrentWithInfo extends AdapterTorrent {
  language: LanguageEnum;
  resolution: ResolutionEnum;
  seeders: number;
}

export interface AdapterParsedTorrent {
  torrentId: string;
  torrentBuffer: Buffer;
}
