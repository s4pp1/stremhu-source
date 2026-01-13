import { ApiProperty } from '@nestjs/swagger';
import { IsBoolean, IsNumber } from 'class-validator';

export class RelaySettingsDto {
  @IsNumber()
  @ApiProperty()
  port: number;

  @IsNumber()
  @ApiProperty()
  downloadLimit: number;

  @IsNumber()
  @ApiProperty()
  uploadLimit: number;

  @IsNumber()
  @ApiProperty()
  connectionsLimit: number;

  @IsNumber()
  @ApiProperty()
  torrentConnectionsLimit: number;

  @IsBoolean()
  @ApiProperty()
  enableUpnpAndNatpmp: boolean;
}
