import { ApiProperty } from '@nestjs/swagger';
import { IsEnum, IsString } from 'class-validator';

import { AudioSpatialEnum } from 'src/preference-items/enum/audio-feature.enum';

export class AudioSpatialMetaDto {
  @IsEnum(AudioSpatialEnum)
  @ApiProperty({ enum: AudioSpatialEnum, enumName: 'AudioSpatialEnum' })
  value: AudioSpatialEnum;

  @IsString()
  @ApiProperty()
  label: string;
}
