import { Expose } from 'class-transformer';
import { IsString } from 'class-validator';

export class CatalogHealthDto {
  /** Katalógus verziója */
  @IsString()
  @Expose()
  version: string;
}
