import { Module } from '@nestjs/common';

import { AuthModule } from 'src/auth/auth.module';
import { CatalogModule } from 'src/catalog/catalog.module';
import { SettingsModule } from 'src/settings/settings.module';
import { TorrentsModule } from 'src/torrents/torrents.module';
import { TrackersMetaModule } from 'src/trackers/meta/trackers-meta.module';
import { TrackersModule } from 'src/trackers/trackers.module';
import { UserPreferencesModule } from 'src/user-preferences/user-preferences.module';

import { StreamsController } from './streams.controller';
import { StreamsService } from './streams.service';

@Module({
  imports: [
    AuthModule,
    SettingsModule,
    TrackersModule,
    TrackersMetaModule,
    CatalogModule,
    TorrentsModule,
    UserPreferencesModule,
  ],
  providers: [StreamsService],
  controllers: [StreamsController],
})
export class StreamsModule {}
