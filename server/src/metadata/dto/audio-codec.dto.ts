import { ApiProperty } from '@nestjs/swagger';
import { IsEnum, IsString } from 'class-validator';

import { AudioCodecEnum } from 'src/stremio/streams/enum/audio-codec.enum';

export class AudioCodecDto {
  @IsEnum(AudioCodecEnum)
  @ApiProperty({ enum: AudioCodecEnum, enumName: 'AudioCodecEnum' })
  value: AudioCodecEnum;

  @IsString()
  @ApiProperty()
  label: string;
}
