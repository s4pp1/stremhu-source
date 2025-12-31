import { Module } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';

import { AuthModule } from 'src/auth/auth.module';
import { LibtorrentModule } from 'src/clients/libtorrent/libtorrent.module';
import { LibtorrentService } from 'src/clients/libtorrent/libtorrent.service';
import { WebTorrentModule } from 'src/clients/webtorrent/webtorrent.module';
import { WebTorrentService } from 'src/clients/webtorrent/webtorrent.service';
import { TorrentClientEnum } from 'src/config/enum/torrent-client.enum';
import { TorrentsCacheCoreModule } from 'src/torrents-cache/core/torrents-cache-core.module';
import { TrackersCoreModule } from 'src/trackers/core/trackers-core.module';

import { TorrentsCoreModule } from './core/torrents-core.module';
import { TorrentsController } from './torrents.controller';
import { TorrentsService } from './torrents.service';

@Module({
  imports: [
    TorrentsCoreModule,
    AuthModule,
    WebTorrentModule,
    LibtorrentModule,
    TorrentsCacheCoreModule,
    TrackersCoreModule,
  ],
  providers: [
    TorrentsService,
    {
      provide: 'TorrentClient',
      inject: [ConfigService, LibtorrentService, WebTorrentService],
      useFactory: (
        config: ConfigService,
        libtorrent: LibtorrentService,
        webtorrent: WebTorrentService,
      ) => {
        const client = config.getOrThrow<TorrentClientEnum>('torrent.client');
        switch (client) {
          case TorrentClientEnum.LIBTORRENT:
            return libtorrent;
          case TorrentClientEnum.WEB_TORRENT:
            return webtorrent;
        }
      },
    },
  ],
  controllers: [TorrentsController],
  exports: [TorrentsService],
})
export class TorrentsModule {}
