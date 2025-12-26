import { Module } from '@nestjs/common';

import { AuthModule } from 'src/auth/auth.module';
import { TorrentsCacheCoreModule } from 'src/torrents-cache/core/torrents-cache-core.module';
import { TorrentsModule } from 'src/torrents/torrents.module';
import { TrackersModule } from 'src/trackers/trackers.module';

import { PlaybackController } from './playback.controller';
import { PlaybackService } from './playback.service';

@Module({
  imports: [
    AuthModule,
    TorrentsCacheCoreModule,
    TorrentsModule,
    TrackersModule,
  ],
  providers: [PlaybackService],
  controllers: [PlaybackController],
})
export class PlaybackModule {}
