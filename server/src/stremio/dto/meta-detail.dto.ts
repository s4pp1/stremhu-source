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
  released?: string;

  /** Megjelenés éve */
  year?: string;

  /** Előzetesek listája */
  trailers?: MetaTrailerDto[];

  /**
   * Csatornákhoz és sorozatokhoz használatos.
   *
   * Ha nincs megadva (pl. filmnél), a Stremio feltételezi, hogy egy videó van, aminek az ID-ja megegyezik a meta ID-val.
   */
  videos?: MetaVideoDto[];

  /**
   * Várható játékidő emberi formátumban.
   *
   * e.g. "120m"
   */
  runtime?: string;

  /** Beszélt nyelv */
  language?: string;

  /** Származási ország */
  country?: string;

  /** Díjak leírása */
  awards?: string;

  /** Hivatalos weboldal URL */
  website?: string;

  /** Viselkedési tippek */
  behaviorHints?: MetaDetailBehaviorHintsDto;

  /** Írók listája */
  writer?: string[];
}
