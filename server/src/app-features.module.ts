import { Module } from '@nestjs/common';

import { AuthModule } from './auth/auth.module';
import { CatalogClientModule } from './catalog-client/catalog-client.module';
import { LocalIpModule } from './local-ip/local-ip.module';
import { MetadataModule } from './metadata/metadata.module';
import { SessionsModule } from './sessions/sessions.module';
import { SettingsModule } from './settings/settings.module';
import { StremioModule } from './stremio/stremio.module';
import { TorrentCacheModule } from './torrent-cache/torrent-cache.module';
import { TrackersModule } from './trackers/trackers.module';
import { UsersModule } from './users/users.module';
import { WebTorrentModule } from './web-torrent/web-torrent.module';

@Module({
  imports: [
    SettingsModule,
    LocalIpModule,
    AuthModule,
    SessionsModule,
    UsersModule,
    MetadataModule,
    TorrentCacheModule,
    WebTorrentModule,
    TrackersModule,
    StremioModule,
    CatalogClientModule,
  ],
})
export class AppFeaturesModule {}
