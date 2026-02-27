import { Module } from '@nestjs/common';

import { AuthModule } from 'src/auth/auth.module';
import { CatalogModule } from 'src/catalog/catalog.module';
import { SettingsModule } from 'src/settings/settings.module';
import { TorrentVideosModule } from 'src/torrent-videos/torrent-videos.module';
import { TorrentsCacheCoreModule } from 'src/torrents-cache/core/torrents-cache-core.module';
import { TorrentsModule } from 'src/torrents/torrents.module';
import { TrackersMetaModule } from 'src/trackers/meta/trackers-meta.module';
import { TrackersModule } from 'src/trackers/trackers.module';
import { UserPreferencesModule } from 'src/users/preferences/user-preferences.module';

import { StremioStreamsController } from './stremio-streams.controller';
import { StremioStreamsService } from './stremio-streams.service';

@Module({
  imports: [
    AuthModule,
    SettingsModule,
    TrackersModule,
    TrackersMetaModule,
    CatalogModule,
    TorrentsModule,
    TorrentsCacheCoreModule,
    UserPreferencesModule,
    TorrentVideosModule,
  ],
  providers: [StremioStreamsService],
  controllers: [StremioStreamsController],
})
export class StremioStreamsModule {}
