import { Module } from '@nestjs/common';

import { AuthModule } from 'src/auth/auth.module';
import { TorrentsCacheCoreModule } from 'src/torrents-cache/core/torrents-cache-core.module';
import { TorrentsModule } from 'src/torrents/torrents.module';
import { TrackersModule } from 'src/trackers/trackers.module';

import { PlayController } from './play.controller';
import { PlayService } from './play.service';

@Module({
  imports: [
    AuthModule,
    TorrentsCacheCoreModule,
    TorrentsModule,
    TrackersModule,
  ],
  providers: [PlayService],
  controllers: [PlayController],
})
export class PlayModule {}
