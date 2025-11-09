import {
  BithumenMovieCategoryEnum,
  BithumenSeriesCategoryEnum,
} from './bithumen.types';

export const BITHUMEN_MOVIE_CATEGORY_FILTERS = Object.values(
  BithumenMovieCategoryEnum,
);
export const BITHUMEN_SERIES_CATEGORY_FILTERS = Object.values(
  BithumenSeriesCategoryEnum,
);

export const BITHUMEN_LOGIN_PATH = '/takelogin.php';
export const BITHUMEN_TORRENTS_PATH = '/browse.php';
export const BITHUMEN_DOWNLOAD_PATH = '/details.php?id={TORRENT_ID}';
export const BITHUMEN_HIT_N_RUN_PATH =
  '/userdetails.php?id={USER_ID}&hnr=1#hnr';
