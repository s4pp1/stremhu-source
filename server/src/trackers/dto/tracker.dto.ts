import { ApiProperty } from '@nestjs/swagger';
import { Exclude } from 'class-transformer';
import { IsBoolean, IsDate, IsEnum, IsNumber, IsString } from 'class-validator';

import { IsNullable } from 'src/common/validators/is-nullable';
import { TrackerEnum } from 'src/trackers/enum/tracker.enum';

export class TrackerDto {
  /** Tracker azonosító */
  @IsEnum(TrackerEnum)
  @ApiProperty({ enum: TrackerEnum, enumName: 'TrackerEnum' })
  tracker: TrackerEnum;

  /** Felhasználónév */
  @IsString()
  username: string;

  @Exclude()
  password: string;

  /** Teljes torrent letöltése */
  @IsBoolean()
  downloadFullTorrent: boolean;

  /** Hit and Run védelem állapota */
  @IsNullable()
  @IsBoolean()
  hitAndRun: boolean | null;

  /** Seedben tartás ideje (másodperc) */
  @IsNullable()
  @IsNumber()
  keepSeedSeconds: number | null;

  /** Utolsó frissítés időpontja */
  @IsDate()
  updatedAt: Date;

  /** Létrehozás időpontja */
  @IsDate()
  createdAt: Date;
}
