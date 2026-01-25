import { Module } from '@nestjs/common';

import { AuthModule } from 'src/auth/auth.module';
import { AppSettingsModule } from 'src/settings/app/app-settings.module';
import { TorrentsCacheCoreModule } from 'src/torrents-cache/core/torrents-cache-core.module';
import { TorrentsCacheModule } from 'src/torrents-cache/torrents-cache.module';
import { TorrentsModule } from 'src/torrents/torrents.module';

import { BithumenModule } from './adapters/bithumen/bithumen.module';
import { InsaneModule } from './adapters/insane/insane.module';
import { MajomparadeModule } from './adapters/majomparade/majomparade.module';
import { NcoreModule } from './adapters/ncore/ncore.module';
import { TrackersCoreModule } from './core/trackers-core.module';
import { TrackerAdapterRegistry } from './tracker-adapter.registry';
import { TrackerDiscoveryService } from './tracker-discovery.service';
import { TrackerMaintenanceService } from './tracker-maintenance.service';
import { TrackersController } from './trackers.controller';
import { TrackersService } from './trackers.service';

@Module({
  imports: [
    TrackersCoreModule,
    AuthModule,
    TorrentsCacheCoreModule,
    TorrentsCacheModule,
    TorrentsModule,
    AppSettingsModule,
    NcoreModule,
    BithumenModule,
    InsaneModule,
    MajomparadeModule,
  ],
  providers: [
    TrackersService,
    TrackerDiscoveryService,
    TrackerMaintenanceService,
    TrackerAdapterRegistry,
  ],
  controllers: [TrackersController],
  exports: [
    TrackersService,
    TrackerDiscoveryService,
    TrackerMaintenanceService,
  ],
})
export class TrackersModule {}
