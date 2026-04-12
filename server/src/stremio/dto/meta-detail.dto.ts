import { Expose } from 'class-transformer';

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
  @Expose()
  released?: string;

  /** Megjelenés éve */
  @Expose()
  year?: string;

  /** Előzetesek listája */
  @Expose()
  trailers?: MetaTrailerDto[];

  /**
   * Csatornákhoz és sorozatokhoz használatos.
   *
   * Ha nincs megadva (pl. filmnél), a Stremio feltételezi, hogy egy videó van, aminek az ID-ja megegyezik a meta ID-val.
   */
  @Expose()
  videos?: MetaVideoDto[];

  /**
   * Várható játékidő emberi formátumban.
   *
   * e.g. "120m"
   */
  @Expose()
  runtime?: string;

  /** Beszélt nyelv */
  @Expose()
  language?: string;

  /** Származási ország */
  @Expose()
  country?: string;

  /** Díjak leírása */
  @Expose()
  awards?: string;

  /** Hivatalos weboldal URL */
  @Expose()
  website?: string;

  /** Viselkedési tippek */
  @Expose()
  behaviorHints?: MetaDetailBehaviorHintsDto;

  /** Írók listája */
  @Expose()
  writer?: string[];
}
