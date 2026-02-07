import { ApiProperty } from '@nestjs/swagger';

import { TrackerEnum } from 'src/trackers/enum/tracker.enum';

export class TorrentDto {
  @ApiProperty({ enum: TrackerEnum, enumName: 'TrackerEnum' })
  tracker: TrackerEnum;

  @ApiProperty()
  name: string;

  @ApiProperty()
  downloadSpeed: number;

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
  torrentId: string;

  @ApiProperty()
  isPersisted: boolean;

  @ApiProperty({ type: 'boolean', nullable: true })
  fullDownload: boolean | null;

  @ApiProperty({ type: 'string', format: 'date-time' })
  lastPlayedAt: Date;

  @ApiProperty({ type: 'string', format: 'date-time' })
  updatedAt: Date;

  @ApiProperty({ type: 'string', format: 'date-time' })
  createdAt: Date;
}
