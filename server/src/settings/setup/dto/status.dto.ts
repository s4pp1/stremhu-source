import { ApiProperty } from '@nestjs/swagger';
import { IsBoolean } from 'class-validator';

export class StatusDto {
  @IsBoolean()
  @ApiProperty()
  hasAdminUser: boolean;

  @IsBoolean()
  @ApiProperty()
  hasAddress: boolean;
}
