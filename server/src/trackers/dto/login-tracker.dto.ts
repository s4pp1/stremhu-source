import { ApiProperty } from '@nestjs/swagger';
import { IsEnum, IsString } from 'class-validator';

import { TrackerEnum } from 'src/trackers/enum/tracker.enum';

export class LoginTrackerDto {
  @IsEnum(TrackerEnum)
  @ApiProperty({
    enum: TrackerEnum,
    enumName: 'TrackerEnum',
  })
  tracker: TrackerEnum;

  @IsString()
  @ApiProperty()
  username: string;

  @IsString()
  @ApiProperty()
  password: string;
}
