import { Expose, Type } from 'class-transformer';

import { MetaPreviewDto } from './meta-preview.dto';
import { StremioCacheDto } from './stremio-cache.dto';

export class StremioCatalogDto extends StremioCacheDto {
  /** Meta adatok előnézeteinek listája */
  @Type(() => MetaPreviewDto)
  @Expose()
  metas: MetaPreviewDto[];
}
