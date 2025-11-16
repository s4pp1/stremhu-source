import { ApiProperty } from '@nestjs/swagger';
import { IsBoolean, IsString } from 'class-validator';

export class StatusDto {
  @IsString()
  @ApiProperty()
  version: string;

  @IsBoolean()
  @ApiProperty()
  configured: boolean;
}
