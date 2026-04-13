import { Module } from '@nestjs/common';

import { KodiStreamsCoreModule } from './streams/core/kodi-streams-core.module';
import { KodiStreamsIntegrationModule } from './streams/integration/kodi-streams-integration.module';

@Module({
  imports: [KodiStreamsCoreModule, KodiStreamsIntegrationModule],
})
export class KodiModule {}
