import {
  DiabloMovieCategoryEnum,
  DiabloSeriesCategoryEnum,
} from './diablo.types';

export const DIABLO_MOVIE_CATEGORY_FILTERS = Object.values(
  DiabloMovieCategoryEnum,
);
export const DIABLO_SERIES_CATEGORY_FILTERS = Object.values(
  DiabloSeriesCategoryEnum,
);

export const DIABLO_INDEX_PATH = '/index';
export const DIABLO_LOGIN_PATH = '/login/run';
export const DIABLO_TORRENTS_PATH = '/browse';
export const DIABLO_DETAILS_PATH = '/details';
export const DIABLO_HIT_N_RUN_PATH = '/hitnrun';
