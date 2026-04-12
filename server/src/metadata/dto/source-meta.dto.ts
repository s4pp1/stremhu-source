import { ApiProperty } from '@nestjs/swagger';
import { IsEnum, IsString } from 'class-validator';

import { SourceEnum } from 'src/preference-items/enum/source.enum';

export class SourceMetaDto {
  /** Forrás típusa */
  @IsEnum(SourceEnum)
  @ApiProperty({ enum: SourceEnum, enumName: 'SourceEnum' })
  value: SourceEnum;

  /** Megjelenített név */
  @IsString()
  label: string;
}
