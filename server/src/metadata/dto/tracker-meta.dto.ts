import { ApiProperty } from '@nestjs/swagger';
import { Expose } from 'class-transformer';
import { IsBoolean, IsEnum, IsString } from 'class-validator';

import { TrackerEnum } from 'src/trackers/enum/tracker.enum';

export class TrackerMetaDto {
  /** Tracker azonosító */
  @Expose()
  @IsEnum(TrackerEnum)
  @ApiProperty({ enum: TrackerEnum, enumName: 'TrackerEnum' })
  value: TrackerEnum;

  /** Megjelenített név */
  @Expose()
  @IsString()
  label: string;

  /** Szükséges-e a teljes letöltés */
  @Expose()
  @IsBoolean()
  requiresFullDownload: boolean;

  /** Weboldal URL */
  @Expose()
  @IsString()
  url: string;

  /** Részletek útvonala */
  @Expose()
  @IsString()
  detailsPath: string;
}
