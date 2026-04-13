import { Module } from '@nestjs/common';

import { StremioStreamsCoreModule } from './core/stremio-streams-core.module';
import { StremioStreamsIntegrationModule } from './integration/stremio-streams-integration.module';

@Module({
  imports: [StremioStreamsCoreModule, StremioStreamsIntegrationModule],
})
export class StremioStreamsModule {}
