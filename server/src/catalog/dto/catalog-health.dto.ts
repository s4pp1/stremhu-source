import { ApiProperty } from '@nestjs/swagger';
import { IsString } from 'class-validator';

export class CatalogHealthDto {
  @IsString()
  @ApiProperty()
  version: string;
}
