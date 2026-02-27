import { Module } from '@nestjs/common';

import { AuthModule } from 'src/auth/auth.module';
import { SettingsModule } from 'src/settings/settings.module';

import { StremioCatalogsModule } from './catalogs/stremio-catalogs.module';
import { StremioStreamsModule } from './streams/stremio-streams.module';
import { StremioController } from './stremio.controller';
import { StremioService } from './stremio.service';

@Module({
  imports: [
    AuthModule,
    SettingsModule,
    StremioStreamsModule,
    StremioCatalogsModule,
  ],
  providers: [StremioService],
  controllers: [StremioController],
})
export class StremioModule {}
