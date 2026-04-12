import { IsString } from 'class-validator';

export class HealthDto {
  /** Az alkalmazás verziója */
  @IsString()
  version: string;
}
