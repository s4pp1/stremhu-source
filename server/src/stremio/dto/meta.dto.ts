import { ApiProperty } from '@nestjs/swagger';

import { MetaDetailDto } from './meta-detail.dto';
import { StremioCacheDto } from './stremio-cache.dto';

export class MetaDto extends StremioCacheDto {
  @ApiProperty({ type: MetaDetailDto })
  meta: MetaDetailDto;
}
