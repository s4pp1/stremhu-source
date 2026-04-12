import { ApiProperty } from '@nestjs/swagger';
import { Expose, Type } from 'class-transformer';

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
  @Expose()
  id: string;

  /** IMDb azonosító */
  @Expose()
  imdb_id?: string;

  /**
   * Type of the content.
   */
  @ApiProperty({ enum: ContentTypeEnum, enumName: 'ContentTypeEnum' })
  @Expose()
  type: ContentTypeEnum;

  /**
   * Name of the content.
   */
  @Expose()
  name: string;

  /**
   * URL to PNG of poster.
   *
   * Accepted aspect ratios: 1:0.675 (IMDb poster type) or 1:1 (square).
   *
   * You can use any resolution, as long as the file size is below 100kb.
   * Below 50kb is recommended
   */
  @Expose()
  poster?: string;

  /**
   * Poster can be square (1:1 aspect) or regular (1:0.675) or landscape (1:1.77).
   *
   * Defaults to 'regular'.
   */
  @ApiProperty({ enum: PosterShapeEnum, enumName: 'PosterShapeEnum' })
  @Expose()
  posterShape?: PosterShapeEnum;

  /**
   * The background shown on the stremio detail page.
   *
   * Heavily encouraged if you want your content to look good.
   *
   * URL to PNG, max file size 500kb.
   */
  @Expose()
  background?: string;

  /**
   * The logo shown on the stremio detail page.
   *
   * Encouraged if you want your content to look good.
   *
   * URL to PNG.
   */
  @Expose()
  logo?: string;

  /**
   * A few sentences describing your content.
   */
  @Expose()
  description?: string;

  /** IMDb értékelés */
  @Expose()
  imdbRating?: string;

  /** Megjelenési információk */
  @Expose()
  releaseInfo?: string;

  /** Műfajok listája */
  @Expose()
  genres?: string[];

  /** Szereplőgárda */
  @Expose()
  cast?: string[];

  /** Rendező(k) */
  @Expose()
  director?: string[];

  /**
   * Can be used to link to internal pages of Stremio.
   *
   * example: array of actor / genre / director links.
   */
  @Type(() => MetaLinkDto)
  @Expose()
  links?: MetaLinkDto[];
}
