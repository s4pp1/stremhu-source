import { ApiProperty } from '@nestjs/swagger';
import { IsEnum, IsString } from 'class-validator';

import { SourceEnum } from 'src/preference-items/enum/source.enum';

export class SourceMetaDto {
  @IsEnum(SourceEnum)
  @ApiProperty({ enum: SourceEnum, enumName: 'SourceEnum' })
  value: SourceEnum;

  @IsString()
  @ApiProperty()
  label: string;
}
