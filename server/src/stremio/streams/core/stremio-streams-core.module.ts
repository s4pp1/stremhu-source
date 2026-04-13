import { Module } from '@nestjs/common';

import { TorrentVideosModule } from 'src/torrent-videos/torrent-videos.module';

import { StremioStreamsCoreService } from './stremio-streams-core.service';

@Module({
  imports: [TorrentVideosModule],
  providers: [StremioStreamsCoreService],
  exports: [StremioStreamsCoreService],
})
export class StremioStreamsCoreModule {}
