import { Module } from '@nestjs/common';

import { AuthModule } from 'src/auth/auth.module';

import { PlayCoreModule } from '../core/play-core.module';
import { PlayIntegrationController } from './play-integration.controller';

@Module({
  imports: [AuthModule, PlayCoreModule],
  controllers: [PlayIntegrationController],
})
export class PlayIntegrationModule {}
