import { ApiProperty } from '@nestjs/swagger';

import { TrackerEnum } from 'src/trackers/enum/tracker.enum';

export class TorrentDto {
  @ApiProperty({ enum: TrackerEnum, enumName: 'TrackerEnum' })
  tracker: TrackerEnum;

  @ApiProperty()
  name: string;

  @ApiProperty()
  uploadSpeed: number;

  @ApiProperty()
  progress: number;

  @ApiProperty()
  downloaded: number;

  @ApiProperty()
  uploaded: number;

  @ApiProperty()
  total: number;

  @ApiProperty()
  infoHash: string;

  @ApiProperty()
  isPersisted: boolean;
}
