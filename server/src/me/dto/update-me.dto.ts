import { IsBoolean, IsNumber, IsOptional, IsString } from 'class-validator';

export class UpdateMeDto {
  /** Felhasználónév */
  @IsOptional()
  @IsString()
  username?: string;

  /** Jelszó */
  @IsOptional()
  @IsString()
  password?: string;

  /** Torrent seed limit */
  @IsOptional()
  @IsNumber()
  torrentSeed?: number | null;

  /** Csak a legjobb torrentek megjelenítése */
  @IsOptional()
  @IsBoolean()
  onlyBestTorrent?: boolean;
}
