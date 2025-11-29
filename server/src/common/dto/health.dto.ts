import { ApiProperty } from '@nestjs/swagger';
import { IsString } from 'class-validator';

export class HealthDto {
  @IsString()
  @ApiProperty()
  version: string;
}
