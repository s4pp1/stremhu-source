import { ApiPropertyOptional } from '@nestjs/swagger';
import { Type } from 'class-transformer';
import { IsInt, Min, ValidateIf } from 'class-validator';

export class FindKodiImdbStreamsDto {
  @ValidateIf(
    (payload: FindKodiImdbStreamsDto) =>
      payload.season !== undefined || payload.episode !== undefined,
  )
  @Type(() => Number)
  @IsInt()
  @Min(1)
  @ApiPropertyOptional({ type: 'integer' })
  season?: number;

  @ValidateIf(
    (payload: FindKodiImdbStreamsDto) =>
      payload.season !== undefined || payload.episode !== undefined,
  )
  @Type(() => Number)
  @IsInt()
  @Min(1)
  @ApiPropertyOptional({ type: 'integer' })
  episode?: number;
}
