import { ApiProperty } from '@nestjs/swagger';

import { ManifestConfigTypeEnum } from '../enum/manifest-config-type.enum';

export class ManifestConfigDto {
  @ApiProperty()
  key: string;

  @ApiProperty({ enum: ManifestConfigTypeEnum })
  type: ManifestConfigTypeEnum;

  @ApiProperty()
  default?: string;

  @ApiProperty()
  title?: string;

  @ApiProperty()
  options?: string[];

  @ApiProperty()
  required?: string;
}
