import { Expose, Type } from 'class-transformer';
import { IsArray } from 'class-validator';

import { KodiImdbStreamDto } from './kodi-imdb-stream.dto';

export class KodiImdbStreamsDto {
  /** Elérhető streamek listája */
  @IsArray()
  @Type(() => KodiImdbStreamDto)
  @Expose()
  streams: KodiImdbStreamDto[];

  /** Hibák listája */
  @Expose()
  errors: string[];
}
