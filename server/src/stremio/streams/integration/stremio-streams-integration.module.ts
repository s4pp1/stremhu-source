import { Module } from '@nestjs/common';

import { AuthModule } from 'src/auth/auth.module';

import { StremioStreamsCoreModule } from '../core/stremio-streams-core.module';
import { StremioStreamsIntegrationController } from './stremio-streams-integration.controller';

@Module({
  imports: [AuthModule, StremioStreamsCoreModule],
  controllers: [StremioStreamsIntegrationController],
})
export class StremioStreamsIntegrationModule {}
