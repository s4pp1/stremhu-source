import { Expose } from 'class-transformer';
import { IsString } from 'class-validator';

export class HealthDto {
  /** Az alkalmazás verziója */
  @IsString()
  @Expose()
  version: string;
}
