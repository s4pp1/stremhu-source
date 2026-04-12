import { Expose } from 'class-transformer';
import { IsBoolean, IsNumber, IsOptional } from 'class-validator';

import { IsNullable } from 'src/common/validators/is-nullable';

export class UpdateTrackerDto {
  /** Hit and Run védelem állapota */
  @IsOptional()
  @IsNullable()
  @IsBoolean()
  @Expose()
  hitAndRun?: boolean | null;

  /** Seedben tartás ideje (másodperc) */
  @IsOptional()
  @IsNullable()
  @IsNumber()
  @Expose()
  keepSeedSeconds?: number | null;

  /** Teljes torrent letöltése */
  @IsOptional()
  @IsBoolean()
  @Expose()
  downloadFullTorrent?: boolean;
}
