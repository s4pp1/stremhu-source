import { IsBoolean, IsOptional } from 'class-validator';

import { IsNullable } from 'src/common/validators/is-nullable';

export class UpdateTorrentDto {
  /** Mentve van-e az adatbázisba */
  @IsOptional()
  @IsBoolean()
  isPersisted?: boolean;

  /** Teljes letöltés állapota */
  @IsOptional()
  @IsNullable()
  @IsBoolean()
  fullDownload?: boolean | null;
}
