import { ApiProperty } from '@nestjs/swagger';
import { IsEnum, IsString } from 'class-validator';

import { LanguageEnum } from 'src/preference-items/enum/language.enum';

export class LanguageDto {
  @IsEnum(LanguageEnum)
  @ApiProperty({ enum: LanguageEnum, enumName: 'LanguageEnum' })
  value: LanguageEnum;

  @IsString()
  @ApiProperty()
  label: string;
}
