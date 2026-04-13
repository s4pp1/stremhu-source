import { IsBoolean, IsNumber, IsOptional, Max, Min } from 'class-validator';

export class UpdateRelaySettingsDto {
  /** Port azonosító */
  @IsOptional()
  @IsNumber()
  @Min(1)
  @Max(65535)
  port?: number;

  /** Letöltési korlát */
  @IsOptional()
  @IsNumber()
  @Min(0)
  downloadLimit?: number;

  /** Feltöltési korlát */
  @IsOptional()
  @IsNumber()
  @Min(0)
  uploadLimit?: number;

  /** Kapcsolatok korlátja */
  @IsOptional()
  @IsNumber()
  @Min(0)
  connectionsLimit?: number;

  /** Torrentenkénti kapcsolatok korlátja */
  @IsOptional()
  @IsNumber()
  @Min(0)
  torrentConnectionsLimit?: number;

  /** UPnP és NAT-PMP engedélyezése */
  @IsOptional()
  @IsBoolean()
  enableUpnpAndNatpmp?: boolean;
}
