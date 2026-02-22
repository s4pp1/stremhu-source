import { Module } from '@nestjs/common';

import { AuthModule } from 'src/auth/auth.module';
import { SettingsModule } from 'src/settings/settings.module';

import { StremioCatalogsModule } from './catalogs/stremio-catalogs.module';
import { PlaybackModule } from './playback/playback.module';
import { StreamsModule } from './streams/streams.module';
import { ManifestController } from './stremio.controller';
import { ManifestService } from './stremio.service';

@Module({
  imports: [
    AuthModule,
    SettingsModule,
    StreamsModule,
    PlaybackModule,
    StremioCatalogsModule,
  ],
  providers: [ManifestService],
  controllers: [ManifestController],
  exports: [ManifestService],
})
export class StremioModule {}
