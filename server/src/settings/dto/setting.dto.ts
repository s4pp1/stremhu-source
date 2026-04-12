import { IsBoolean, IsNumber, IsString } from 'class-validator';

import { IsNullable } from 'src/common/validators/is-nullable';

export class SettingDto {
  /** Local IP engedélyezése */
  @IsBoolean()
  enebledlocalIp: boolean;

  /** Cím */
  @IsString()
  @IsNullable()
  address: string | null;

  /** Hit and Run védelem */
  @IsBoolean()
  hitAndRun: boolean;

  /** Seedben tartás ideje (másodperc) */
  @IsNumber()
  keepSeedSeconds: number;

  /** Cache megőrzési ideje (másodperc) */
  @IsNumber()
  cacheRetentionSeconds: number;

  /** Katalógus token */
  @IsString()
  catalogToken: string | null;
}
