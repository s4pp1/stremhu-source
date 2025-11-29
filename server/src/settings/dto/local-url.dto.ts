import { ApiProperty } from '@nestjs/swagger';
import { IsString } from 'class-validator';

export class LocalUrlDto {
  @IsString()
  @ApiProperty()
  localUrl: string;
}
