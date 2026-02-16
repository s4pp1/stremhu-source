import { ApiProperty } from '@nestjs/swagger';
import { IsArray, IsEnum } from 'class-validator';

import { PreferenceEnum } from '../enum/preference.enum';

export class ReorderPreferencesDto {
  @IsArray()
  @IsEnum(PreferenceEnum, { each: true })
  @ApiProperty({
    enum: PreferenceEnum,
    enumName: 'PreferenceEnum',
    isArray: true,
  })
  preferences: PreferenceEnum[];
}
