import { MetaDetailDto } from './meta-detail.dto';
import { StremioCacheDto } from './stremio-cache.dto';

export class MetaDto extends StremioCacheDto {
  /** Meta adatok részletei */
  meta: MetaDetailDto;
}
