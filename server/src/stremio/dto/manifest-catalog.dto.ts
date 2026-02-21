import { ApiProperty } from '@nestjs/swagger';

import { ContentTypeEnum } from '../enum/content-type.enum';
import { ManifestExtraDto } from './manifest-extra.dto';

export class ManifestCatalog {
  @ApiProperty({ enum: ContentTypeEnum })
  type: ContentTypeEnum;

  @ApiProperty()
  id: string;

  @ApiProperty()
  name: string;

  @ApiProperty({ type: ManifestExtraDto, isArray: true })
  extra?: ManifestExtraDto[];
}
