import { Module } from '@nestjs/common';

import { StremioCatalogsCoreModule } from './core/stremio-catalogs-core.module';
import { StremioCatalogsIntegrationModule } from './integration/stremio-catalogs-integration.module';

@Module({
  imports: [StremioCatalogsCoreModule, StremioCatalogsIntegrationModule],
})
export class StremioCatalogsModule {}
