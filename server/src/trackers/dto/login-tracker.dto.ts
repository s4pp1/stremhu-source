import { ApiProperty } from '@nestjs/swagger';
import { IsEnum, IsString } from 'class-validator';

import { TrackerEnum } from 'src/trackers/enum/tracker.enum';

export class LoginTrackerDto {
  /** Tracker azonosító */
  @IsEnum(TrackerEnum)
  @ApiProperty({ enum: TrackerEnum, enumName: 'TrackerEnum' })
  tracker: TrackerEnum;

  /** Felhasználónév */
  @IsString()
  username: string;

  /** Jelszó */
  @IsString()
  password: string;
}
