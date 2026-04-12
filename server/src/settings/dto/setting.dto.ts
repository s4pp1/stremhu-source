import { Expose } from 'class-transformer';
import { IsBoolean, IsNumber, IsString } from 'class-validator';

import { IsNullable } from 'src/common/validators/is-nullable';

export class SettingDto {
  /** Local IP engedélyezése */
  @IsBoolean()
  @Expose()
  enebledlocalIp: boolean;

  /** Cím */
  @IsString()
  @IsNullable()
  @Expose()
  address: string | null;

  /** Hit and Run védelem */
  @IsBoolean()
  @Expose()
  hitAndRun: boolean;

  /** Seedben tartás ideje (másodperc) */
  @IsNumber()
  @Expose()
  keepSeedSeconds: number;

  /** Cache megőrzési ideje (másodperc) */
  @IsNumber()
  @Expose()
  cacheRetentionSeconds: number;

  /** Katalógus token */
  @IsString()
  @Expose()
  catalogToken: string | null;
}
