import { ApiProperty } from '@nestjs/swagger';
import { Exclude, Expose } from 'class-transformer';
import { IsBoolean, IsDate, IsEnum, IsNumber, IsString } from 'class-validator';

import { IsNullable } from 'src/common/validators/is-nullable';
import { TrackerEnum } from 'src/trackers/enum/tracker.enum';

export class TrackerDto {
  /** Tracker azonosító */
  @IsEnum(TrackerEnum)
  @ApiProperty({ enum: TrackerEnum, enumName: 'TrackerEnum' })
  @Expose()
  tracker: TrackerEnum;

  /** Felhasználónév */
  @IsString()
  @Expose()
  username: string;

  @Exclude()
  @Expose()
  password: string;

  /** Teljes torrent letöltése */
  @IsBoolean()
  @Expose()
  downloadFullTorrent: boolean;

  /** Hit and Run védelem állapota */
  @IsNullable()
  @IsBoolean()
  @Expose()
  hitAndRun: boolean | null;

  /** Seedben tartás ideje (másodperc) */
  @IsNullable()
  @IsNumber()
  @Expose()
  keepSeedSeconds: number | null;

  /** Utolsó frissítés időpontja */
  @IsDate()
  @Expose()
  updatedAt: Date;

  /** Létrehozás időpontja */
  @IsDate()
  @Expose()
  createdAt: Date;
}
