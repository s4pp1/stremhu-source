import { ApiProperty } from '@nestjs/swagger';
import { IsNumber, IsOptional } from 'class-validator';

export class UpdateExternalSettingDto {
  @IsOptional()
  @IsNumber()
  @ApiProperty({ type: 'number', required: false })
  port?: number;
}
