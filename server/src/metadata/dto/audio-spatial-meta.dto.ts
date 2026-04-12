import { ApiProperty } from '@nestjs/swagger';
import { IsEnum, IsString } from 'class-validator';

import { AudioSpatialEnum } from 'src/preference-items/enum/audio-feature.enum';

export class AudioSpatialMetaDto {
  /** Térhatású hang értéke */
  @IsEnum(AudioSpatialEnum)
  @ApiProperty({ enum: AudioSpatialEnum, enumName: 'AudioSpatialEnum' })
  value: AudioSpatialEnum;

  /** Megjelenített név */
  @IsString()
  label: string;
}
