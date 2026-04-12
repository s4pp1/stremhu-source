import { IsString } from 'class-validator';

export class CatalogHealthDto {
  /** Katalógus verziója */
  @IsString()
  version: string;
}
