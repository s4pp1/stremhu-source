import { ApiProperty } from '@nestjs/swagger';
import {
  IsBoolean,
  IsNumber,
  IsOptional,
  IsString,
  IsUrl,
  Validate,
} from 'class-validator';

import { IsNullable } from 'src/common/validators/is-nullable';
import { NoPathDomain } from 'src/common/validators/no-path-domain';

export class UpdateSettingDto {
  @IsOptional()
  @IsBoolean()
  @ApiProperty({ required: false })
  enebledlocalIp: boolean;

  @IsOptional()
  @IsUrl({
    protocols: ['https'],
    require_protocol: true,
    require_valid_protocol: true,
    require_host: true,
    allow_fragments: false,
    allow_query_components: false,
  })
  @Validate(NoPathDomain)
  @ApiProperty({ required: false })
  endpoint: string;

  @IsOptional()
  @IsNumber()
  @ApiProperty({ required: false })
  uploadLimit: number;

  @IsOptional()
  @IsBoolean()
  @ApiProperty({ required: false })
  hitAndRun: boolean;

  @IsOptional()
  @IsNullable()
  @IsString()
  @ApiProperty({ nullable: true, required: false })
  cacheRetention?: string | null;

  @IsOptional()
  @IsNullable()
  @IsString()
  @ApiProperty({ nullable: true, required: false })
  catalogToken?: string | null;
}
