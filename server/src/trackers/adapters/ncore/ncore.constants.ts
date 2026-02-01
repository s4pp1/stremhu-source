import { NcoreMovieCategoryEnum, NcoreSeriesCategoryEnum } from './ncore.types';

export const MOVIE_CATEGORY_FILTERS = Object.values(NcoreMovieCategoryEnum);
export const SERIES_CATEGORY_FILTERS = Object.values(NcoreSeriesCategoryEnum);

export const LOGIN_PATH = '/login.php';
export const TORRENTS_PATH = '/torrents.php';
export const DETAILS_PATH = `${TORRENTS_PATH}?action=details&id={torrentId}`;
export const HIT_N_RUN_PATH = '/hitnrun.php';
