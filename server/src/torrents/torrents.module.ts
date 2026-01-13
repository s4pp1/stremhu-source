import { Module } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';

import { AuthModule } from 'src/auth/auth.module';
import { LibtorrentModule } from 'src/clients/libtorrent/libtorrent.module';
import { LibtorrentService } from 'src/clients/libtorrent/libtorrent.service';
import { TorrentClientEnum } from 'src/config/enum/torrent-client.enum';
import { RelaySettingsModule } from 'src/settings/relay/relay-settings.module';
import { TorrentsCacheCoreModule } from 'src/torrents-cache/core/torrents-cache-core.module';
import { TrackersCoreModule } from 'src/trackers/core/trackers-core.module';

import { TorrentsCoreModule } from './core/torrents-core.module';
import { TorrentsController } from './torrents.controller';
import { TorrentsService } from './torrents.service';

@Module({
  imports: [
    AuthModule,
    TorrentsCoreModule,
    LibtorrentModule,
    TorrentsCacheCoreModule,
    TrackersCoreModule,
    RelaySettingsModule,
  ],
  providers: [
    TorrentsService,
    {
      provide: 'TorrentClient',
      inject: [ConfigService, LibtorrentService],
      useFactory: (config: ConfigService, libtorrent: LibtorrentService) => {
        const client = config.getOrThrow<TorrentClientEnum>('torrent.client');
        switch (client) {
          case TorrentClientEnum.LIBTORRENT:
            return libtorrent;
        }
      },
    },
  ],
  controllers: [TorrentsController],
  exports: [TorrentsService],
})
export class TorrentsModule {}
