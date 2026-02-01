import {
  BithumenMovieCategoryEnum,
  BithumenSeriesCategoryEnum,
} from './bithumen.types';

export const MOVIE_CATEGORY_FILTERS = Object.values(BithumenMovieCategoryEnum);
export const SERIES_CATEGORY_FILTERS = Object.values(
  BithumenSeriesCategoryEnum,
);

export const INDEX_PATH = '/index.php';
export const LOGIN_PATH = '/takelogin.php';
export const TORRENTS_PATH = '/browse.php';
export const DETAILS_PATH = '/details.php?id={torrentId}';
export const HIT_N_RUN_PATH = '/userdetails.php';
