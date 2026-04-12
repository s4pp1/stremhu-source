import { IsArray } from 'class-validator';

import { KodiImdbStreamDto } from './kodi-imdb-stream.dto';

export class KodiImdbStreamsDto {
  /** Elérhető streamek listája */
  @IsArray()
  streams: KodiImdbStreamDto[];

  /** Hibák listája */
  errors: string[];
}
