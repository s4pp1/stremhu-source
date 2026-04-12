import { ApiProperty } from '@nestjs/swagger';
import { IsEnum, IsString } from 'class-validator';

import { AudioQualityEnum } from 'src/preference-items/enum/audio-quality.enum';

export class AudioQualityMetaDto {
  /** Audió minőség értéke */
  @IsEnum(AudioQualityEnum)
  @ApiProperty({ enum: AudioQualityEnum, enumName: 'AudioQualityEnum' })
  value: AudioQualityEnum;

  /** Megjelenített név */
  @IsString()
  label: string;
}
