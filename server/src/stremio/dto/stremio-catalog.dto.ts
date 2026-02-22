import { ApiProperty } from '@nestjs/swagger';

import { MetaPreviewDto } from './meta-preview.dto';
import { StremioCacheDto } from './stremio-cache.dto';

export class StremioCatalogDto extends StremioCacheDto {
  @ApiProperty({ type: () => MetaPreviewDto, isArray: true })
  metas: MetaPreviewDto[];
}
