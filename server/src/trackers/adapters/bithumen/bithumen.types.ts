export enum BithumenMovieCategoryEnum {
  SD_HUN = '23',
  SD = '19',
  HD_HUN = '25',
  HD = '5',
  FULL_HD_HU = '37',
  FULL_HD = '39',
  BLU_RAY_HU = '33',
  BLU_RAY = '40',
}

export enum BithumenSeriesCategoryEnum {
  SD_HUN = '7',
  SD = '26',
  HD_HUN = '41',
  HD = '42',
}

export type BithumenCategory =
  | BithumenMovieCategoryEnum
  | BithumenSeriesCategoryEnum;

export interface BithumenLoginRequest {
  username: string;
  password: string;
}

export interface BithumenTorrentsQuery {
  categories: string[];
  imdbId: string;
}

export interface BithumenTorrent {
  downloadUrl: string;
  torrentId: string;
  category: BithumenCategory;
  seeders: string;
  imdbId: string;
}

export interface BithumenTorrents {
  results: BithumenTorrent[];
  hasNextPage: boolean;
}
