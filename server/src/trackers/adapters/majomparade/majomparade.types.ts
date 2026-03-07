export enum MajomparadeMovieCategoryEnum {
  CAM_HUN = '6',
  CAM = '5',
  SD_HUN = '14',
  SD = '13',
  HD_HUN = '12',
  HD = '11',
}

export enum MajomparadeSeriesCategoryEnum {
  SD_HUN = '18',
  SD = '17',
  HD_HUN = '19',
  HD = '20',
}

export type MajomparadeLoginResponse = {
  success: boolean;
  text: string;
};

export type MajomparadeCategory =
  | MajomparadeMovieCategoryEnum
  | MajomparadeSeriesCategoryEnum;

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
