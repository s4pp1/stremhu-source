import { ApiProperty } from '@nestjs/swagger';
import { IsEnum, IsString } from 'class-validator';

import { LanguageEnum } from 'src/common/enum/language.enum';

export class LanguageDto {
  @IsEnum(LanguageEnum)
  @ApiProperty({ enum: LanguageEnum, enumName: 'LanguageEnum' })
  value: LanguageEnum;

  @IsString()
  @ApiProperty()
  label: string;
}
