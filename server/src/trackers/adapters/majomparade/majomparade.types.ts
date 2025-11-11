export enum MajomparadeMovieCategoryEnum {
  CAM_HUN = '76',
  CAM = '75',
  SD_HUN = '24',
  SD = '38',
  HD_HUN = '51',
  HD = '42',
}

export enum MajomparadeSeriesCategoryEnum {
  SD_HUN = '36',
  SD = '47',
  HD_HUN = '6',
  HD = '7',
}

export type MajomparadeCategory =
  | MajomparadeMovieCategoryEnum
  | MajomparadeSeriesCategoryEnum;

export interface MajomparadeLoginRequest {
  username: string;
  password: string;
}

export interface MajomparadeTorrentsQuery {
  categories: string[];
  imdbId: string;
}

export interface MajomparadeTorrent {
  downloadUrl: string;
  torrentId: string;
  category: MajomparadeCategory;
  seeders: string;
}

export interface MajomparadeTorrents {
  results: MajomparadeTorrent[];
  hasNextPage: boolean;
}
