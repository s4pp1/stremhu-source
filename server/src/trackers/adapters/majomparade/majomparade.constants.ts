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

export const LOGIN_PATH = '/login.php';
export const TORRENTS_PATH = '/letoltes.php';
export const DETAILS_PATH = '/details.php?id={torrentId}';
export const HIT_N_RUN_PATH = '/hitnrun.php';
