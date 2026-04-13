import { Module } from '@nestjs/common';

import { AuthModule } from 'src/auth/auth.module';

import { StremioCatalogsCoreModule } from '../core/stremio-catalogs-core.module';
import { StremioCatalogsIntegrationController } from './stremio-catalogs-integration.controller';

@Module({
  imports: [AuthModule, StremioCatalogsCoreModule],
  controllers: [StremioCatalogsIntegrationController],
})
export class StremioCatalogsIntegrationModule {}
