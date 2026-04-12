import { MetaPreviewDto } from './meta-preview.dto';
import { StremioCacheDto } from './stremio-cache.dto';

export class StremioCatalogDto extends StremioCacheDto {
  /** Meta adatok előnézeteinek listája */
  metas: MetaPreviewDto[];
}
