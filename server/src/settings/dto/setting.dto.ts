import { ApiProperty } from '@nestjs/swagger';
import { IsBoolean, IsNumber, IsString } from 'class-validator';

import { IsNullable } from 'src/common/validators/is-nullable';

export class SettingDto {
  @IsBoolean()
  @ApiProperty()
  enebledlocalIp: boolean;

  @IsString()
  @IsNullable()
  @ApiProperty({ type: 'string', nullable: true })
  address: string | null;

  @IsNumber()
  @ApiProperty()
  downloadLimit: number;

  @IsNumber()
  @ApiProperty()
  uploadLimit: number;

  @IsBoolean()
  @ApiProperty()
  hitAndRun: boolean;

  @IsString()
  @ApiProperty({ type: 'string', nullable: true })
  cacheRetention: string | null;

  @IsString()
  @ApiProperty({ type: 'string', nullable: true })
  catalogToken: string | null;
}
