import { ApiProperty } from '@nestjs/swagger';
import { Expose } from 'class-transformer';
import { IsBoolean } from 'class-validator';

export class StatusDto {
  @IsBoolean()
  @ApiProperty()
  @Expose()
  hasAdminUser: boolean;

  @IsBoolean()
  @ApiProperty()
  @Expose()
  hasAddress: boolean;
}
