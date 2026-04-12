import { Expose } from 'class-transformer';
import { IsArray } from 'class-validator';

import { KodiImdbStreamDto } from './kodi-imdb-stream.dto';

export class KodiImdbStreamsDto {
  /** Elérhető streamek listája */
  @Expose()
  @IsArray()
  streams: KodiImdbStreamDto[];

  /** Hibák listája */
  @Expose()
  errors: string[];
}
