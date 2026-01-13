import { ApiProperty } from '@nestjs/swagger';
import { IsBoolean, IsNumber, IsOptional, Max, Min } from 'class-validator';

export class UpdateRelaySettingsDto {
  @IsOptional()
  @IsNumber()
  @Min(1)
  @Max(65535)
  @ApiProperty({ type: 'number', required: false })
  port: number;

  @IsOptional()
  @IsNumber()
  @Min(0)
  @ApiProperty({ type: 'number', required: false })
  downloadLimit: number;

  @IsOptional()
  @IsNumber()
  @Min(0)
  @ApiProperty({ type: 'number', required: false })
  uploadLimit: number;

  @IsOptional()
  @IsNumber()
  @Min(0)
  @ApiProperty({ type: 'number', required: false })
  connectionsLimit: number;

  @IsOptional()
  @IsNumber()
  @Min(0)
  @ApiProperty({ type: 'number', required: false })
  torrentConnectionsLimit: number;

  @IsOptional()
  @IsBoolean()
  @ApiProperty({ type: 'boolean', required: false })
  enableUpnpAndNatpmp?: boolean;
}
