import { Module } from '@nestjs/common';

import { AuthModule } from 'src/auth/auth.module';
import { RelayModule } from 'src/relay/relay.module';
import { RelaySettingsModule } from 'src/settings/relay/relay-settings.module';
import { TorrentsCacheCoreModule } from 'src/torrents-cache/core/torrents-cache-core.module';
import { TrackersCoreModule } from 'src/trackers/core/trackers-core.module';

import { TorrentsCoreModule } from './core/torrents-core.module';
import { ExternalRelaySettingsController } from './external-relay-settings.controller';
import { TorrentsController } from './torrents.controller';
import { TorrentsService } from './torrents.service';

@Module({
  imports: [
    AuthModule,
    TorrentsCoreModule,
    RelayModule,
    TorrentsCacheCoreModule,
    TrackersCoreModule,
    RelaySettingsModule,
  ],
  providers: [TorrentsService],
  controllers: [TorrentsController, ExternalRelaySettingsController],
  exports: [TorrentsService],
})
export class TorrentsModule {}
