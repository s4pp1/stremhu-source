import { Module } from '@nestjs/common';

import { AuthModule } from 'src/auth/auth.module';
import { TorrentVideosModule } from 'src/torrent-videos/torrent-videos.module';

import { KodiStreamsController } from './kodi-streams.controller';
import { KodiStreamsService } from './kodi-streams.service';

@Module({
  imports: [AuthModule, TorrentVideosModule],
  providers: [KodiStreamsService],
  controllers: [KodiStreamsController],
})
export class KodiStreamsModule {}
