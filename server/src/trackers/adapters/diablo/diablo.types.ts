export enum DiabloMovieCategoryEnum {
  SD_HUN = '101',
  SD = '102',
  HD_HUN = '103',
  HD = '104',
  CAM_HU = '21',
  CAM = '49',
}

export enum DiabloSeriesCategoryEnum {
  SD_HUN = '107',
  SD = '108',
  HD_HUN = '111',
  HD = '112',
}

export type DiabloCategory = DiabloMovieCategoryEnum | DiabloSeriesCategoryEnum;

export interface DiabloTorrentsQuery {
  categories: string[];
  imdbId: string;
}

export interface DiabloTorrent {
  downloadUrl: string;
  torrentId: string;
  category: DiabloCategory;
  seeders: string;
}

export interface DiabloTorrents {
  results: DiabloTorrent[];
  hasNextPage: boolean;
}
