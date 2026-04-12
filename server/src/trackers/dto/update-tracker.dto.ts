import { IsBoolean, IsNumber, IsOptional } from 'class-validator';

import { IsNullable } from 'src/common/validators/is-nullable';

export class UpdateTrackerDto {
  /** Hit and Run védelem állapota */
  @IsOptional()
  @IsNullable()
  @IsBoolean()
  hitAndRun?: boolean | null;

  /** Seedben tartás ideje (másodperc) */
  @IsOptional()
  @IsNullable()
  @IsNumber()
  keepSeedSeconds?: number | null;

  /** Teljes torrent letöltése */
  @IsOptional()
  @IsBoolean()
  downloadFullTorrent?: boolean;
}
