import { Module } from '@nestjs/common';

import { AuthModule } from 'src/auth/auth.module';

import { StremioCoreModule } from '../core/stremio-core.module';
import { StremioIntegrationController } from './stremio-integration.controller';

@Module({
  imports: [AuthModule, StremioCoreModule],
  controllers: [StremioIntegrationController],
})
export class StremioIntegrationModule {}
