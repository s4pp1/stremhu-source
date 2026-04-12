import { ApiProperty } from '@nestjs/swagger';
import { Expose } from 'class-transformer';
import { IsEnum, IsString } from 'class-validator';

import { TrackerEnum } from 'src/trackers/enum/tracker.enum';

export class LoginTrackerDto {
  /** Tracker azonosító */
  @IsEnum(TrackerEnum)
  @ApiProperty({ enum: TrackerEnum, enumName: 'TrackerEnum' })
  @Expose()
  tracker: TrackerEnum;

  /** Felhasználónév */
  @IsString()
  @Expose()
  username: string;

  /** Jelszó */
  @IsString()
  @Expose()
  password: string;
}
