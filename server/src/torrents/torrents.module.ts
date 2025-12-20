import { Module } from '@nestjs/common';

import { AuthModule } from 'src/auth/auth.module';
import { WebTorrentModule } from 'src/clients/webtorrent/webtorrent.module';
import { WebTorrentService } from 'src/clients/webtorrent/webtorrent.service';
import { TorrentsCacheCoreModule } from 'src/torrents-cache/core/torrents-cache-core.module';

import { TorrentsCoreModule } from './core/torrents-core.module';
import { TorrentsController } from './torrents.controller';
import { TorrentsService } from './torrents.service';

@Module({
  imports: [
    TorrentsCoreModule,
    AuthModule,
    WebTorrentModule,
    TorrentsCacheCoreModule,
  ],
  providers: [
    TorrentsService,
    { provide: 'TorrentClient', useExisting: WebTorrentService },
  ],
  controllers: [TorrentsController],
  exports: [TorrentsService],
})
export class TorrentsModule {}
