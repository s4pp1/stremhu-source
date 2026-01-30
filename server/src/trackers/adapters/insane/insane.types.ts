export enum MovieCategoryEnum {
  SD_HUN = '41',
  SD = '42',
  HD_HUN = '27',
  HD = '25',
  UHD_HUN = '44',
  UHD = '45',
}

export enum SeriesCategoryEnum {
  SD_HUN = '8',
  SD = '7',
  HD_HUN = '40',
  HD = '39',
  UHD_HUN = '47',
  UHD = '46',
}

export type CategoryEnum = MovieCategoryEnum | SeriesCategoryEnum;

export interface TorrentsQuery {
  categories: string[];
  imdbId: string;
}

export interface Torrent {
  downloadUrl: string;
  torrentId: string;
  category: CategoryEnum;
  seeders: string;
  imdbId: string;
}

export interface Torrents {
  results: Torrent[];
  hasNextPage: boolean;
}
