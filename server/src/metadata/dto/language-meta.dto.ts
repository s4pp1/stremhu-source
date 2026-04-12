import { ApiProperty } from '@nestjs/swagger';
import { IsEnum, IsString } from 'class-validator';

import { LanguageEnum } from 'src/preference-items/enum/language.enum';

export class LanguageMetaDto {
  /** Nyelv értéke */
  @IsEnum(LanguageEnum)
  @ApiProperty({ enum: LanguageEnum, enumName: 'LanguageEnum' })
  value: LanguageEnum;

  /** Megjelenített név */
  @IsString()
  label: string;
}
