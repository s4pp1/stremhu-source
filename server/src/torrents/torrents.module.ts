import { Module } from '@nestjs/common';

import { AuthModule } from 'src/auth/auth.module';
import { RelayModule } from 'src/relay/relay.module';
import { RelaySettingsModule } from 'src/settings/relay/relay-settings.module';
import { TrackersCoreModule } from 'src/trackers/core/trackers-core.module';

import { ExternalRelaySettingsController } from './external-relay-settings.controller';
import { PersistedTorrentsCoreModule } from './persisted/core/persisted-torrents-core.module';
import { PersistedTorrentsModule } from './persisted/persisted-torrents.module';
import { TorrentsController } from './torrents.controller';
import { TorrentsService } from './torrents.service';

@Module({
  imports: [
    AuthModule,
    PersistedTorrentsCoreModule,
    PersistedTorrentsModule,
    RelayModule,
    TrackersCoreModule,
    RelaySettingsModule,
  ],
  providers: [TorrentsService],
  controllers: [TorrentsController, ExternalRelaySettingsController],
  exports: [TorrentsService],
})
export class TorrentsModule {}
