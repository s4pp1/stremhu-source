import { ApiProperty } from '@nestjs/swagger';
import { IsBoolean, IsEnum, IsString } from 'class-validator';

import { TrackerEnum } from 'src/trackers/enum/tracker.enum';

export class TrackerMetaDto {
  /** Tracker azonosító */
  @IsEnum(TrackerEnum)
  @ApiProperty({ enum: TrackerEnum, enumName: 'TrackerEnum' })
  value: TrackerEnum;

  /** Megjelenített név */
  @IsString()
  label: string;

  /** Szükséges-e a teljes letöltés */
  @IsBoolean()
  requiresFullDownload: boolean;

  /** Weboldal URL */
  @IsString()
  url: string;

  /** Részletek útvonala */
  @IsString()
  detailsPath: string;
}
