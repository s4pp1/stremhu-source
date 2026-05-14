import { ParsedStreamSeries } from 'src/stremio/streams/type/parsed-stream-series.type';

export enum FilelistCommonCategoryEnum {
  ANIME = '24',
}

export enum FilelistMovieCategoryEnum {
  SD = '1',
  DVD = '2',
  HD = '4',
  UHD = '6',
  BLU_RAY = '20',
  UHD_BLU_RAY = '26',
  ANIME = FilelistCommonCategoryEnum.ANIME,
}

export enum FilelistSeriesCategoryEnum {
  HD = '21',
  SD = '23',
  UHD = '27',
  ANIME = FilelistCommonCategoryEnum.ANIME,
}

export type FilelistCategory =
  | FilelistMovieCategoryEnum
  | FilelistSeriesCategoryEnum;

export interface FilelistTorrentsQuery {
  categories: string[];
  imdbId: string;
  series?: ParsedStreamSeries;
}

export interface FilelistTorrent {
  downloadUrl: string;
  torrentId: string;
  category: FilelistCategory;
  seeders: string;
  imdbId: string;
  name?: string;
}

export interface FilelistTorrents {
  results: FilelistTorrent[];
  hasNextPage: boolean;
}

export enum FilelistSearchInByEnum {
  NAME_DESCRIPTION = 0,
  NAME = 1,
  DESCRIPTION = 2,
  IMDB = 3,
}

export enum FilelistSortByEnum {
  HYBRID = 0,
  RELEVANCE = 1,
  DATE = 2,
  SIZE = 3,
  DOWNLOADS = 4,
  PEERS = 5,
}
