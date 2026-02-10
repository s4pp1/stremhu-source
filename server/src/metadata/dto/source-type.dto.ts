import { ApiProperty } from '@nestjs/swagger';
import { IsEnum, IsString } from 'class-validator';

import { SourceTypeEnum } from 'src/preference-items/enum/source-type.enum';

export class SourceTypeDto {
  @IsEnum(SourceTypeEnum)
  @ApiProperty({ enum: SourceTypeEnum, enumName: 'SourceTypeEnum' })
  value: SourceTypeEnum;

  @IsString()
  @ApiProperty()
  label: string;
}
