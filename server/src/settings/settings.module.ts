import { Module } from '@nestjs/common';

import { AuthModule } from 'src/auth/auth.module';
import { CatalogModule } from 'src/catalog/catalog.module';
import { LocalIpModule } from 'src/local-ip/local-ip.module';
import { TorrentCacheModule } from 'src/torrent-cache/torrent-cache.module';
import { TrackersModule } from 'src/trackers/trackers.module';
import { UsersModule } from 'src/users/users.module';
import { WebTorrentModule } from 'src/web-torrent/web-torrent.module';

import { SettingsCoreModule } from './core/settings-core.module';
import { SettingsController } from './settings.controller';
import { SettingsService } from './settings.service';
import { SetupModule } from './setup/setup.module';

@Module({
  imports: [
    SettingsCoreModule,
    AuthModule,
    UsersModule,
    SetupModule,
    TrackersModule,
    WebTorrentModule,
    LocalIpModule,
    TorrentCacheModule,
    CatalogModule,
  ],
  providers: [SettingsService],
  controllers: [SettingsController],
  exports: [SettingsService],
})
export class SettingsModule {}
