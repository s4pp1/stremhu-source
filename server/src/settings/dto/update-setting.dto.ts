import { ApiProperty } from '@nestjs/swagger';
import {
  IsBoolean,
  IsNumber,
  IsOptional,
  IsString,
  IsUrl,
  Validate,
  ValidateIf,
} from 'class-validator';

import { IsIPv4 } from 'src/common/validators/is-ip-v4';
import { IsNullable } from 'src/common/validators/is-nullable';
import { NoPathDomain } from 'src/common/validators/no-path-domain';

export class UpdateSettingDto {
  @IsOptional()
  @IsBoolean()
  @ApiProperty({ required: false })
  enebledlocalIp?: boolean;

  @IsOptional()
  @ValidateIf((setting: UpdateSettingDto) => setting.enebledlocalIp === false)
  @IsUrl({
    protocols: ['https'],
    require_protocol: true,
    require_valid_protocol: true,
    require_host: true,
    allow_fragments: false,
    allow_query_components: false,
  })
  @Validate(NoPathDomain)
  @ValidateIf((setting: UpdateSettingDto) => setting.enebledlocalIp === true)
  @Validate(IsIPv4)
  @ApiProperty({ required: false })
  address?: string;

  @IsOptional()
  @IsNumber()
  @ApiProperty({ required: false })
  downloadLimit?: number;

  @IsOptional()
  @IsNumber()
  @ApiProperty({ required: false })
  uploadLimit?: number;

  @IsOptional()
  @IsBoolean()
  @ApiProperty({ required: false })
  hitAndRun?: boolean;

  @IsOptional()
  @IsNullable()
  @IsNumber()
  @ApiProperty({ type: 'number', nullable: true, required: false })
  keepSeedSeconds?: number | null;

  @IsOptional()
  @IsNullable()
  @IsNumber()
  @ApiProperty({ type: 'number', nullable: true, required: false })
  cacheRetentionSeconds?: number | null;

  @IsOptional()
  @IsNullable()
  @IsString()
  @ApiProperty({ type: 'string', nullable: true, required: false })
  catalogToken?: string | null;
}
