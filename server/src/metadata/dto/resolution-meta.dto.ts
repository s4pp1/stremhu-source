import { ApiProperty } from '@nestjs/swagger';
import { Expose } from 'class-transformer';
import { IsEnum, IsString } from 'class-validator';

import { ResolutionEnum } from 'src/preference-items/enum/resolution.enum';

export class ResolutionMetaDto {
  /** Felbontás értéke */
  @Expose()
  @IsEnum(ResolutionEnum)
  @ApiProperty({ enum: ResolutionEnum, enumName: 'ResolutionEnum' })
  value: ResolutionEnum;

  /** Megjelenített név */
  @Expose()
  @IsString()
  label: string;
}
