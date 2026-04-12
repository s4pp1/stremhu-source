import { Expose, Type } from 'class-transformer';

import { MetaDetailDto } from './meta-detail.dto';
import { StremioCacheDto } from './stremio-cache.dto';

export class MetaDto extends StremioCacheDto {
  /** Meta adatok részletei */
  @Type(() => MetaDetailDto)
  @Expose()
  meta: MetaDetailDto;
}
