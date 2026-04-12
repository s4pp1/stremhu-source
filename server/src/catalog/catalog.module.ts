import { Module } from '@nestjs/common';

import { AppSettingsModule } from 'src/settings/app/app-settings.module';

import { CatalogController } from './catalog.controller';
import { CatalogService } from './catalog.service';

@Module({
  imports: [AppSettingsModule],
  providers: [CatalogService],
  controllers: [CatalogController],
  exports: [CatalogService],
})
export class CatalogModule {}
