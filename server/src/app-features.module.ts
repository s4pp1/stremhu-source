import { Module } from '@nestjs/common';

import { AuthModule } from './auth/auth.module';
import { CatalogModule } from './catalog/catalog.module';
import { LocalIpModule } from './local-ip/local-ip.module';
import { MeModule } from './me/me.module';
import { MetadataModule } from './metadata/metadata.module';
import { SessionsModule } from './sessions/sessions.module';
import { SettingsModule } from './settings/settings.module';
import { StremioModule } from './stremio/stremio.module';
import { TorrentsCacheModule } from './torrents-cache/torrents-cache.module';
import { TorrentsModule } from './torrents/torrents.module';
import { TrackersModule } from './trackers/trackers.module';
import { UsersModule } from './users/users.module';

@Module({
  imports: [
    SettingsModule,
    LocalIpModule,
    AuthModule,
    SessionsModule,
    UsersModule,
    MeModule,
    MetadataModule,
    TorrentsCacheModule,
    TorrentsModule,
    TrackersModule,
    StremioModule,
    CatalogModule,
  ],
})
export class AppFeaturesModule {}
