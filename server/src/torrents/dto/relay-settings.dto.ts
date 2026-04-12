import { Expose } from 'class-transformer';
import { IsBoolean, IsNumber } from 'class-validator';

export class RelaySettingsDto {
  /** Port azonosító */
  @Expose()
  @IsNumber()
  port: number;

  /** Letöltési korlát */
  @Expose()
  @IsNumber()
  downloadLimit: number;

  /** Feltöltési korlát */
  @Expose()
  @IsNumber()
  uploadLimit: number;

  /** Kapcsolatok korlátja */
  @Expose()
  @IsNumber()
  connectionsLimit: number;

  /** Torrentenkénti kapcsolatok korlátja */
  @Expose()
  @IsNumber()
  torrentConnectionsLimit: number;

  /** UPnP és NAT-PMP engedélyezése */
  @Expose()
  @IsBoolean()
  enableUpnpAndNatpmp: boolean;
}
