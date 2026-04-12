import { ApiProperty } from '@nestjs/swagger';
import { IsArray, IsEnum } from 'class-validator';

import { PreferenceEnum } from '../enum/preference.enum';

export class ReorderPreferencesDto {
  /** A preferenciák új sorrendje */
  @IsArray()
  @IsEnum(PreferenceEnum, { each: true })
  @ApiProperty({
    enum: PreferenceEnum,
    enumName: 'PreferenceEnum',
  })
  preferences: PreferenceEnum[];
}
