import { Module } from '@nestjs/common';

import { PersistedTorrentsModule } from 'src/torrents/persisted/persisted-torrents.module';
import { TrackersCoreModule } from 'src/trackers/core/trackers-core.module';
import { TrackersModule } from 'src/trackers/trackers.module';

import { RelayRuntimeService } from './relay-runtime.service';
import { RelayModule } from './relay.module';

@Module({
  imports: [
    RelayModule,
    PersistedTorrentsModule,
    TrackersCoreModule,

    TrackersModule,
  ],
  providers: [RelayRuntimeService],
})
export class RelayRuntimeModule {}
