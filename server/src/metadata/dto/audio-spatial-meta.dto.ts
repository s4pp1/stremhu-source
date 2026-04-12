import { ApiProperty } from '@nestjs/swagger';
import { Expose } from 'class-transformer';
import { IsEnum, IsString } from 'class-validator';

import { AudioSpatialEnum } from 'src/preference-items/enum/audio-feature.enum';

export class AudioSpatialMetaDto {
  /** Térhatású hang jellemző értéke */
  @Expose()
  @IsEnum(AudioSpatialEnum)
  @ApiProperty({ enum: AudioSpatialEnum, enumName: 'AudioSpatialEnum' })
  value: AudioSpatialEnum;

  /** Megjelenített név */
  @Expose()
  @IsString()
  label: string;
}
