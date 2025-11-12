export enum NcoreMovieCategoryEnum {
  SD_HUN = 'xvid_hun',
  SD = 'xvid',
  HD_HUN = 'hd_hun',
  HD = 'hd',
}

export enum NcoreSeriesCategoryEnum {
  SD_HUN = 'xvidser_hun',
  SD = 'xvidser',
  HD_HUN = 'hdser_hun',
  HD = 'hdser',
}

export type NcoreCategory = NcoreMovieCategoryEnum | NcoreSeriesCategoryEnum;

export interface NcoreLoginRequest {
  username: string;
  password: string;
}

export enum NcoreSearchByEnum {
  NAME = 'name',
  DESCRIPTION = 'leiras',
  IMDB = 'imdb',
  TAGS = 'cimke',
}

export enum NcoreSearchTypeEnum {
  SELECTED = 'kivalasztottak_kozott',
}

export enum NcoreOrderByEnum {
  NAME = 'name',
  CREATION_TIME = 'ctime',
  SEEDERS = 'seeders',
  TIMES_COMPLETED = 'times_completed',
  SIZE = 'size',
  LEECHERS = 'leechers',
}

export enum NcoreOrderDirectionEnum {
  DESC = 'DESC',
  ASC = 'ASC',
}

export enum NcoreTorrentTypeEnum {
  MOVIE = 'movie',
  SERIES = 'show',
}

export interface NcoreSearchParams {
  oldal: number;
  mire: string;
  miben: NcoreSearchByEnum;
  miszerint: NcoreOrderByEnum;
  hogyan: NcoreOrderDirectionEnum;
  tipus: NcoreSearchTypeEnum;
  kivalasztott_tipus: Array<NcoreCategory>;
  jsons: boolean;
}

export interface NcoreFindQuery {
  imdbId: string;
  categories: NcoreCategory[];
}

export interface NcoreTorrents {
  results: NcoreTorrent[];
  total_results: string;
  onpage: number;
  perpage: string;
}

export interface NcoreTorrent {
  category: NcoreCategory;
  torrent_id: string;
  release_name: string;
  details_url: string;
  download_url: string;
  freeleech: boolean;
  imdb_id: string;
  imdb_rating: string;
  size: string;
  type: NcoreTorrentTypeEnum;
  leechers: string;
  seeders: string;
}

export interface NcoreDownloadRequest {
  torrentId: string;
  downloadUrl: string;
}
