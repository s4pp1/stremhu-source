import { Module } from '@nestjs/common';

import { TorrentVideosModule } from 'src/torrent-videos/torrent-videos.module';

import { KodiStreamsCoreService } from './kodi-streams-core.service';

@Module({
  imports: [TorrentVideosModule],
  providers: [KodiStreamsCoreService],
  exports: [KodiStreamsCoreService],
})
export class KodiStreamsCoreModule {}
