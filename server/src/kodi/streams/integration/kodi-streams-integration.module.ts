import { Module } from '@nestjs/common';

import { AuthModule } from 'src/auth/auth.module';

import { KodiStreamsCoreModule } from '../core/kodi-streams-core.module';
import { KodiIntegrationController } from './kodi-streams-integration.controller';

@Module({
  imports: [AuthModule, KodiStreamsCoreModule],
  controllers: [KodiIntegrationController],
})
export class KodiStreamsIntegrationModule {}
