import { Module } from '@nestjs/common';

import { StremioCatalogsModule } from './catalogs/stremio-catalogs.module';
import { StremioIntegrationModule } from './integration/stremio-integration.module';
import { StremioStreamsModule } from './streams/stremio-streams.module';

@Module({
  imports: [
    StremioIntegrationModule,
    StremioStreamsModule,
    StremioCatalogsModule,
  ],
})
export class StremioModule {}
