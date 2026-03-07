import {
  MajomparadeMovieCategoryEnum,
  MajomparadeSeriesCategoryEnum,
} from './majomparade.types';

export const MOVIE_CATEGORY_FILTERS = Object.values(
  MajomparadeMovieCategoryEnum,
);
export const SERIES_CATEGORY_FILTERS = Object.values(
  MajomparadeSeriesCategoryEnum,
);

export const LOGIN_PATH = '/login/do';
export const TORRENTS_PATH = '/torrents';
export const DETAILS_PATH = '/torrent/{torrentId}';
export const HIT_N_RUN_PATH = '/hitnrun.php';
