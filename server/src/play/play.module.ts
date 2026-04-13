import { Module } from '@nestjs/common';

import { PlayCoreModule } from './core/play-core.module';
import { PlayIntegrationModule } from './integration/play-integration.module';

@Module({
  imports: [PlayCoreModule, PlayIntegrationModule],
})
export class PlayModule {}
