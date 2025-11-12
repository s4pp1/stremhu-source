import { NcoreMovieCategoryEnum, NcoreSeriesCategoryEnum } from './ncore.types';

export const NCORE_MOVIE_CATEGORY_FILTERS = Object.values(
  NcoreMovieCategoryEnum,
);
export const NCORE_SERIES_CATEGORY_FILTERS = Object.values(
  NcoreSeriesCategoryEnum,
);

export const NCORE_LOGIN_PATH = '/login.php';
export const NCORE_TORRENTS_PATH = '/torrents.php';
export const NCORE_HIT_N_RUN_PATH = '/hitnrun.php';
