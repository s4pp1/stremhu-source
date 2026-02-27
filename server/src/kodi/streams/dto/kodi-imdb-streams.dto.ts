import { ApiProperty } from '@nestjs/swagger';
import { IsArray } from 'class-validator';

import { KodiImdbStreamDto } from './kodi-imdb-stream.dto';

export class KodiImdbStreamsDto {
  @IsArray()
  @ApiProperty({
    type: KodiImdbStreamDto,
    isArray: true,
  })
  streams: KodiImdbStreamDto[];

  @ApiProperty({
    type: 'string',
    isArray: true,
  })
  errors: string[];
}
