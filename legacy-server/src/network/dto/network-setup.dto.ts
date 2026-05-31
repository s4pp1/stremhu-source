import { ApiProperty } from '@nestjs/swagger';
import {
  IsBoolean,
  IsEmail,
  IsEnum,
  IsNotEmpty,
  IsString,
  IsUrl,
  Validate,
  ValidateIf,
} from 'class-validator';

import { NoPathDomain } from 'src/common/validators/no-path-domain';
import { NetworkConnectionEnum } from 'src/settings/enum/network-connection.enum';
import { NetworkProviderEnum } from 'src/settings/enum/network-provider.enum';

import { NetworkSetupModeEnum } from '../enum/network-setup-mode.enum';

export class NetworkBaseSetupDto {
  @ApiProperty({ enum: NetworkSetupModeEnum })
  @IsEnum(NetworkSetupModeEnum)
  mode: NetworkSetupModeEnum;

  @IsUrl({
    allow_protocol_relative_urls: true,
    require_protocol: true,
    require_valid_protocol: true,
    require_host: true,
    allow_fragments: false,
    allow_query_components: false,
  })
  @Validate(NoPathDomain)
  host: string;
}

export class NetworkAutoSetupDto extends NetworkBaseSetupDto {
  @ApiProperty({ enum: [NetworkSetupModeEnum.AUTO] })
  declare mode: NetworkSetupModeEnum.AUTO;

  @ApiProperty({ enum: NetworkProviderEnum })
  @IsEnum(NetworkProviderEnum)
  provider: NetworkProviderEnum;

  @ApiProperty({ enum: NetworkConnectionEnum })
  @IsEnum(NetworkConnectionEnum)
  connection: NetworkConnectionEnum;

  @IsString()
  @IsNotEmpty()
  token: string;

  @IsEmail()
  email: string;
}

export class NetworkManualSetupDto extends NetworkBaseSetupDto {
  @ApiProperty({ enum: [NetworkSetupModeEnum.MANUAL] })
  declare mode: NetworkSetupModeEnum.MANUAL;

  @IsBoolean()
  reverseProxy: boolean;
}

export class NetworkSetupDto extends NetworkBaseSetupDto {
  @ValidateIf((o: NetworkSetupDto) => o.mode === NetworkSetupModeEnum.AUTO)
  @IsEnum(NetworkConnectionEnum)
  @IsNotEmpty()
  connection: NetworkConnectionEnum;

  @ValidateIf((o: NetworkSetupDto) => o.mode === NetworkSetupModeEnum.AUTO)
  @IsString()
  @IsNotEmpty()
  token: string;

  @ValidateIf((o: NetworkSetupDto) => o.mode === NetworkSetupModeEnum.AUTO)
  @IsEmail()
  @IsNotEmpty()
  email: string;

  @ValidateIf((o: NetworkSetupDto) => o.mode === NetworkSetupModeEnum.MANUAL)
  @IsEnum(NetworkProviderEnum)
  @IsNotEmpty()
  provider: NetworkProviderEnum;

  @ValidateIf((o: NetworkSetupDto) => o.mode === NetworkSetupModeEnum.MANUAL)
  @IsBoolean()
  reverseProxy: boolean;
}
