import { ApiProperty } from '@nestjs/swagger';
import { Expose } from 'class-transformer';
import { IsEnum, IsString } from 'class-validator';

import { SourceEnum } from 'src/preference-items/enum/source.enum';

export class SourceMetaDto {
  /** Forrás értéke */
  @Expose()
  @IsEnum(SourceEnum)
  @ApiProperty({ enum: SourceEnum, enumName: 'SourceEnum' })
  value: SourceEnum;

  /** Megjelenített név */
  @Expose()
  @IsString()
  label: string;
}
