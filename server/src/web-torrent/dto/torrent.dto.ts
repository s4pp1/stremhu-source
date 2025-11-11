import { ApiProperty } from '@nestjs/swagger';

import { TrackerEnum } from 'src/trackers/enums/tracker.enum';

export class TorrentDto {
  @ApiProperty({ enum: TrackerEnum, enumName: 'TrackerEnum' })
  tracker: TrackerEnum;

  @ApiProperty()
  name: string;

  @ApiProperty()
  uploadSpeed: string;

  @ApiProperty()
  progress: string;

  @ApiProperty()
  downloaded: string;

  @ApiProperty()
  uploaded: string;

  @ApiProperty()
  total: string;

  @ApiProperty()
  infoHash: string;
}
