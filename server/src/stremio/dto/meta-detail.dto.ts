import { ApiProperty } from '@nestjs/swagger';

import { MetaDetailBehaviorHintsDto } from './meta-detail-behaviour-hints.dto';
import { MetaPreviewDto } from './meta-preview.dto';
import { MetaTrailerDto } from './meta-trailer.dto';
import { MetaVideoDto } from './meta-video.dto';

export class MetaDetailDto extends MetaPreviewDto {
  /**
   * ISO 8601, initial release date.
   *
   * For movies, this is the cinema debut.
   *
   * e.g. "2010-12-06T05:00:00.000Z"
   */
  @ApiProperty({ required: false })
  released?: string;

  @ApiProperty({ required: false })
  year?: string;

  @ApiProperty({ type: () => MetaTrailerDto, isArray: true, required: false })
  trailers?: MetaTrailerDto[];

  /**
   * Used for channel and series.
   *
   * If you do not provide this (e.g. for movie), Stremio assumes this meta item has one video, and it's ID is equal to the meta item id.
   */
  @ApiProperty({ type: () => MetaVideoDto, isArray: true, required: false })
  videos?: MetaVideoDto[];

  /**
   * Human-readable expected runtime.
   *
   * e.g. "120m"
   */
  @ApiProperty({ required: false })
  runtime?: string;

  /**
   * Spoken language.
   */
  @ApiProperty({ required: false })
  language?: string;

  /**
   * Official country of origin.
   */
  @ApiProperty({ required: false })
  country?: string;

  /**
   * Human-readable that describes all the significant awards.
   */
  @ApiProperty({ required: false })
  awards?: string;

  /**
   * URL to official website.
   */
  @ApiProperty({ required: false })
  website?: string;

  @ApiProperty({
    type: () => MetaDetailBehaviorHintsDto,
    required: false,
  })
  behaviorHints?: MetaDetailBehaviorHintsDto;

  @ApiProperty({ type: 'string', isArray: true, required: false })
  writer?: string[];
}
