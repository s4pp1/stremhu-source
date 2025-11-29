import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';

import { WebTorrentRun } from './entity/web-torrent-run.entity';
import { WebTorrentRunsService } from './web-torrent-runs.service';

@Module({
  imports: [TypeOrmModule.forFeature([WebTorrentRun])],
  providers: [WebTorrentRunsService],
  exports: [WebTorrentRunsService],
})
export class WebTorrentRunsModule {}
