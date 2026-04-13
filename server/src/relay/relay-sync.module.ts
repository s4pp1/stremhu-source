import { Module } from '@nestjs/common';

import { SettingsCoreModule } from 'src/settings/core/settings-core.module';
import { PersistedTorrentsModule } from 'src/torrents/persisted/persisted-torrents.module';
import { TrackersCoreModule } from 'src/trackers/core/trackers-core.module';
import { TrackersModule } from 'src/trackers/trackers.module';

import { RelayCoreModule } from './core/relay-core.module';
import { RelaySyncService } from './relay-sync.service';

@Module({
  imports: [
    RelayCoreModule,
    SettingsCoreModule,
    PersistedTorrentsModule,
    TrackersCoreModule,
    TrackersModule,
  ],
  providers: [RelaySyncService],
  exports: [RelaySyncService],
})
export class RelaySyncModule {}
