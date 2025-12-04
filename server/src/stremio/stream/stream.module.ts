import { Module } from '@nestjs/common';

import { AuthModule } from 'src/auth/auth.module';
import { CatalogModule } from 'src/catalog/catalog.module';
import { SettingsCoreModule } from 'src/settings/core/settings-core.module';
import { TorrentCacheCoreModule } from 'src/torrent-cache/core/torrent-cache-core.module';
import { TrackersModule } from 'src/trackers/trackers.module';
import { UsersModule } from 'src/users/users.module';
import { WebTorrentModule } from 'src/web-torrent/web-torrent.module';

import { StremioStreamController } from './stream.controller';
import { StremioStreamService } from './stream.service';

@Module({
  imports: [
    AuthModule,
    UsersModule,
    SettingsCoreModule,
    WebTorrentModule,
    TrackersModule,
    TorrentCacheCoreModule,
    CatalogModule,
  ],
  controllers: [StremioStreamController],
  providers: [StremioStreamService],
  exports: [],
})
export class StremioStreamModule {}
