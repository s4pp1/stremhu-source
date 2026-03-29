import { Module } from '@nestjs/common';

import { RelaySettingsModule } from 'src/settings/relay/relay-settings.module';
import { PersistedTorrentsModule } from 'src/torrents/persisted/persisted-torrents.module';
import { TrackersCoreModule } from 'src/trackers/core/trackers-core.module';
import { TrackersModule } from 'src/trackers/trackers.module';

import { RelaySyncService } from './relay-sync.service';
import { RelayModule } from './relay.module';

@Module({
  imports: [
    RelayModule,
    RelaySettingsModule,
    PersistedTorrentsModule,
    TrackersCoreModule,
    TrackersModule,
  ],
  providers: [RelaySyncService],
  exports: [RelaySyncService],
})
export class RelaySyncModule {}
