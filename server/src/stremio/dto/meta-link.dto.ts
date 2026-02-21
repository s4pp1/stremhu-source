import { ApiProperty } from '@nestjs/swagger';

export class MetaLinkDto {
  /** Megjelenített név pl. "Action", "Christopher Nolan" */
  @ApiProperty()
  name: string;

  /** Kategória pl. "Genres" | "Cast" | "Writers" | "Directors"*/
  @ApiProperty()
  category: string;

  /** URL – lehet stremio:/// meta link is */
  @ApiProperty()
  url: string;
}
