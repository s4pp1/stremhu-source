import { Expose } from 'class-transformer';
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
  /** Local IP engedélyezése */
  @IsOptional()
  @IsBoolean()
  @Expose()
  enebledlocalIp?: boolean;

  /** Cím */
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
  @Expose()
  address?: string;

  /** Hit and Run védelem */
  @IsOptional()
  @IsBoolean()
  @Expose()
  hitAndRun?: boolean;

  /** Seedben tartás ideje (másodperc) */
  @IsOptional()
  @IsNullable()
  @IsNumber()
  @Expose()
  keepSeedSeconds?: number;

  /** Cache megőrzési ideje (másodperc) */
  @IsOptional()
  @IsNullable()
  @IsNumber()
  @Expose()
  cacheRetentionSeconds?: number;

  /** Katalógus token */
  @IsOptional()
  @IsNullable()
  @IsString()
  @Expose()
  catalogToken?: string | null;
}
