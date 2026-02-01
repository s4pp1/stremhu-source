import { ApiProperty } from '@nestjs/swagger';
import { IsBoolean, IsOptional } from 'class-validator';

import { IsNullable } from 'src/common/validators/is-nullable';

export class UpdateTorrentDto {
  @IsOptional()
  @IsBoolean()
  @ApiProperty({ type: 'boolean', required: false })
  isPersisted?: boolean;

  @IsOptional()
  @IsNullable()
  @IsBoolean()
  @ApiProperty({ type: 'boolean', required: false, nullable: true })
  fullDownload?: boolean | null;
}
