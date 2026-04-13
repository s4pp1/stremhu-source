import { Module } from '@nestjs/common';

import { TorrentsCacheCoreModule } from 'src/torrents-cache/core/torrents-cache-core.module';
import { TorrentsModule } from 'src/torrents/torrents.module';
import { TrackersModule } from 'src/trackers/trackers.module';

import { PlayCoreService } from './play-core.service';

@Module({
  imports: [TorrentsCacheCoreModule, TorrentsModule, TrackersModule],
  providers: [PlayCoreService],
  exports: [PlayCoreService],
})
export class PlayCoreModule {}
