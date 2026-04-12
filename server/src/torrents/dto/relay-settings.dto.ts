import { IsBoolean, IsNumber } from 'class-validator';

export class RelaySettingsDto {
  /** Port azonosító */
  @IsNumber()
  port: number;

  /** Letöltési korlát */
  @IsNumber()
  downloadLimit: number;

  /** Feltöltési korlát */
  @IsNumber()
  uploadLimit: number;

  /** Kapcsolatok korlátja */
  @IsNumber()
  connectionsLimit: number;

  /** Torrentenkénti kapcsolatok korlátja */
  @IsNumber()
  torrentConnectionsLimit: number;

  /** UPnP és NAT-PMP engedélyezése */
  @IsBoolean()
  enableUpnpAndNatpmp: boolean;
}
