import { ApiProperty } from '@nestjs/swagger';
import {
  IsBoolean,
  IsNumber,
  IsString,
  IsUrl,
  Validate,
} from 'class-validator';

import { NoPathDomain } from 'src/common/validators/no-path-domain';

export class SettingDto {
  @IsBoolean()
  @ApiProperty()
  enebledlocalIp: boolean;

  @IsUrl({
    protocols: ['https'],
    require_protocol: true,
    require_valid_protocol: true,
    require_host: true,
    allow_fragments: false,
    allow_query_components: false,
  })
  @Validate(NoPathDomain)
  @ApiProperty()
  endpoint: string;

  @IsNumber()
  @ApiProperty()
  uploadLimit: number;

  @IsBoolean()
  @ApiProperty()
  hitAndRun: boolean;

  @IsString()
  @ApiProperty({ nullable: true })
  cacheRetention: string | null;

  @IsString()
  @ApiProperty({ nullable: true })
  catalogToken: string | null;
}
