import { ApiProperty } from '@nestjs/swagger';
import { Expose } from 'class-transformer';
import { IsEnum, IsString } from 'class-validator';

import { AudioQualityEnum } from 'src/preference-items/enum/audio-quality.enum';

export class AudioQualityMetaDto {
  /** Audió minőség értéke */
  @Expose()
  @IsEnum(AudioQualityEnum)
  @ApiProperty({ enum: AudioQualityEnum, enumName: 'AudioQualityEnum' })
  value: AudioQualityEnum;

  /** Megjelenített név */
  @Expose()
  @IsString()
  label: string;
}
