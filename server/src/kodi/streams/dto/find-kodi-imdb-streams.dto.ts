import { Type } from 'class-transformer';
import { IsInt, Min, ValidateIf } from 'class-validator';

export class FindKodiImdbStreamsDto {
  /** Évad száma */
  @ValidateIf(
    (payload: FindKodiImdbStreamsDto) =>
      payload.season !== undefined || payload.episode !== undefined,
  )
  @Type(() => Number)
  @IsInt()
  @Min(1)
  season?: number;

  /** Epizód száma */
  @ValidateIf(
    (payload: FindKodiImdbStreamsDto) =>
      payload.season !== undefined || payload.episode !== undefined,
  )
  @Type(() => Number)
  @IsInt()
  @Min(1)
  episode?: number;
}
