import { ApiProperty } from '@nestjs/swagger';
import { Expose } from 'class-transformer';
import { IsEnum, IsString } from 'class-validator';

import { LanguageEnum } from 'src/preference-items/enum/language.enum';

export class LanguageMetaDto {
  /** Nyelv értéke */
  @Expose()
  @IsEnum(LanguageEnum)
  @ApiProperty({ enum: LanguageEnum, enumName: 'LanguageEnum' })
  value: LanguageEnum;

  /** Megjelenített név */
  @Expose()
  @IsString()
  label: string;
}
