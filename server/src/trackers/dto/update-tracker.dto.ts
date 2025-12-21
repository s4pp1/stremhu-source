import { ApiProperty } from '@nestjs/swagger';
import { IsBoolean, IsNumber, IsOptional } from 'class-validator';

import { IsNullable } from 'src/common/validators/is-nullable';

export class UpdateTrackerDto {
  @IsOptional()
  @IsNullable()
  @IsBoolean()
  @ApiProperty({ type: 'boolean', required: false, nullable: true })
  hitAndRun?: boolean | null;

  @IsOptional()
  @IsNullable()
  @IsNumber()
  @ApiProperty({ type: 'number', required: false, nullable: true })
  keepSeedSeconds?: number | null;

  @IsOptional()
  @IsBoolean()
  @ApiProperty({ type: 'boolean', required: false })
  downloadFullTorrent?: boolean;
}
