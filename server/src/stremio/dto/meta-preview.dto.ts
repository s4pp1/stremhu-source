import { ApiProperty } from '@nestjs/swagger';

import { ContentTypeEnum } from '../enum/content-type.enum';
import { PosterShapeEnum } from '../enum/poster-shape.enum';
import { MetaLinkDto } from './meta-link.dto';

export class MetaPreviewDto {
  /**
   * Universal identifier.
   * You may use a prefix unique to your addon.
   *
   * Example: 'yt_id:UCrDkAvwZum-UTjHmzDI2iIw'
   */
  @ApiProperty()
  id: string;

  @ApiProperty({ type: 'string', required: false })
  imdb_id?: string;

  /**
   * Type of the content.
   */
  @ApiProperty({ enum: ContentTypeEnum, enumName: 'ContentTypeEnum' })
  type: ContentTypeEnum;

  /**
   * Name of the content.
   */
  @ApiProperty()
  name: string;

  /**
   * URL to PNG of poster.
   *
   * Accepted aspect ratios: 1:0.675 (IMDb poster type) or 1:1 (square).
   *
   * You can use any resolution, as long as the file size is below 100kb.
   * Below 50kb is recommended
   */
  @ApiProperty({ required: false })
  poster?: string;

  /**
   * Poster can be square (1:1 aspect) or regular (1:0.675) or landscape (1:1.77).
   *
   * Defaults to 'regular'.
   */
  @ApiProperty({ enum: PosterShapeEnum, enumName: 'PosterShapeEnum' })
  posterShape?: PosterShapeEnum;

  /**
   * The background shown on the stremio detail page.
   *
   * Heavily encouraged if you want your content to look good.
   *
   * URL to PNG, max file size 500kb.
   */
  @ApiProperty({ required: false })
  background?: string;

  /**
   * The logo shown on the stremio detail page.
   *
   * Encouraged if you want your content to look good.
   *
   * URL to PNG.
   */
  @ApiProperty({ required: false })
  logo?: string;

  /**
   * A few sentences describing your content.
   */
  @ApiProperty({ required: false })
  description?: string;

  @ApiProperty({ type: 'string', required: false })
  imdbRating?: string;

  @ApiProperty({ required: false })
  releaseInfo?: string;

  @ApiProperty({ type: 'string', isArray: true, required: false })
  genres?: string[];

  @ApiProperty({ type: 'string', isArray: true, required: false })
  cast?: string[];

  @ApiProperty({ type: 'string', isArray: true, required: false })
  director?: string[];

  /**
   * Can be used to link to internal pages of Stremio.
   *
   * example: array of actor / genre / director links.
   */
  @ApiProperty({ type: () => MetaLinkDto, isArray: true, required: false })
  links?: MetaLinkDto[];
}
