export class MetaLinkDto {
  /** Megjelenített név pl. "Action", "Christopher Nolan" */
  name: string;

  /** Kategória pl. "Genres" | "Cast" | "Writers" | "Directors"*/
  category: string;

  /** URL – lehet stremio:/// meta link is */
  url: string;
}
