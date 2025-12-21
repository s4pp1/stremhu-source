import { ApiProperty } from '@nestjs/swagger';
import { IsBoolean, IsOptional } from 'class-validator';

export class UpdateTorrentDto {
  @IsOptional()
  @IsBoolean()
  @ApiProperty({ type: 'boolean', required: false })
  isPersisted?: boolean;
}
