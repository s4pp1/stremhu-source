import {
  FilelistMovieCategoryEnum,
  FilelistSeriesCategoryEnum,
} from './filelist.types';

export const MOVIE_CATEGORY_FILTERS = Object.values(FilelistMovieCategoryEnum);
export const SERIES_CATEGORY_FILTERS = Object.values(
  FilelistSeriesCategoryEnum,
);

export const LOGIN_PAGE_PATH = '/login.php';
export const LOGIN_PATH = '/takelogin.php';
export const TORRENTS_PATH = '/browse.php';
export const DETAILS_PATH = '/details.php?id={torrentId}';
export const HIT_N_RUN_PATH = '/snatchlist.php';
