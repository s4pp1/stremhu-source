import { Expose } from 'class-transformer';

export class MetaLinkDto {
  /** Megjelenített név pl. "Action", "Christopher Nolan" */
  @Expose()
  name: string;

  /** Kategória pl. "Genres" | "Cast" | "Writers" | "Directors"*/
  @Expose()
  category: string;

  /** URL – lehet stremio:/// meta link is */
  @Expose()
  url: string;
}
