import { Module } from '@nestjs/common';

import { AuthModule } from 'src/auth/auth.module';
import { CatalogModule } from 'src/catalog/catalog.module';
import { LocalIpModule } from 'src/local-ip/local-ip.module';
import { TorrentsCacheModule } from 'src/torrents-cache/torrents-cache.module';
import { TorrentsModule } from 'src/torrents/torrents.module';
import { TrackersModule } from 'src/trackers/trackers.module';
import { UsersModule } from 'src/users/users.module';

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
    TorrentsModule,
    LocalIpModule,
    TorrentsCacheModule,
    CatalogModule,
  ],
  providers: [SettingsService],
  controllers: [SettingsController],
  exports: [SettingsService],
})
export class SettingsModule {}
