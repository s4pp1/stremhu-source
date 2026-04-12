import { Expose } from 'class-transformer';

import { MetaDetailDto } from './meta-detail.dto';
import { StremioCacheDto } from './stremio-cache.dto';

export class MetaDto extends StremioCacheDto {
  /** Meta adatok részletei */
  @Expose()
  meta: MetaDetailDto;
}
