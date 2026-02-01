import { ApiProperty } from '@nestjs/swagger';
import { IsBoolean, IsEnum, IsString } from 'class-validator';

import { TrackerEnum } from 'src/trackers/enum/tracker.enum';

export class TrackerMetaDto {
  @IsEnum(TrackerEnum)
  @ApiProperty({ enum: TrackerEnum, enumName: 'TrackerEnum' })
  value: TrackerEnum;

  @IsString()
  @ApiProperty()
  label: string;

  @IsBoolean()
  @ApiProperty()
  requiresFullDownload: boolean;

  @IsString()
  @ApiProperty()
  url: string;

  @IsString()
  @ApiProperty()
  detailsPath: string;
}
