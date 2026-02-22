import { ApiProperty } from '@nestjs/swagger';

import { ExtraEnum } from '../enum/extra.enum';

export class ManifestExtraDto {
  @ApiProperty({ enum: ExtraEnum })
  name: ExtraEnum;

  @ApiProperty()
  isRequired?: boolean;

  @ApiProperty()
  options?: string[];

  @ApiProperty()
  optionsLimit?: number;
}
