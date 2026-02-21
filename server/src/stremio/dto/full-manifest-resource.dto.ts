import { ApiProperty } from '@nestjs/swagger';

import { ContentTypeEnum } from '../enum/content-type.enum';
import { ShortManifestResourceEnum } from '../enum/short-manifest-resource.enum';

export class FullManifestResourceDto {
  @ApiProperty({ enum: ShortManifestResourceEnum })
  name: ShortManifestResourceEnum;

  @ApiProperty({ enum: ContentTypeEnum, isArray: true })
  types: ContentTypeEnum[];

  @ApiProperty()
  idPrefixes?: string[] | undefined;
}
