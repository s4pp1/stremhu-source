import { Module } from '@nestjs/common';

import { AuthModule } from 'src/auth/auth.module';
import { CatalogModule } from 'src/catalog/catalog.module';
import { SettingsCoreModule } from 'src/settings/core/settings-core.module';
import { TorrentsCacheCoreModule } from 'src/torrents-cache/core/torrents-cache-core.module';
import { TorrentsModule } from 'src/torrents/torrents.module';
import { TrackersModule } from 'src/trackers/trackers.module';

import { StremioStreamController } from './stream.controller';
import { StremioStreamService } from './stream.service';

@Module({
  imports: [
    AuthModule,
    SettingsCoreModule,
    TorrentsModule,
    TrackersModule,
    TorrentsCacheCoreModule,
    CatalogModule,
  ],
  controllers: [StremioStreamController],
  providers: [StremioStreamService],
  exports: [],
})
export class StremioStreamModule {}
