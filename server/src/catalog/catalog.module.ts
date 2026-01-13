import { Module } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';

import { AppSettingsModule } from 'src/settings/app/app-settings.module';

import { CATALOG_CLIENT } from './catalog-client.token';
import { CatalogController } from './catalog.controller';
import { CatalogService } from './catalog.service';
import { CatalogClient } from './client';

@Module({
  imports: [AppSettingsModule],
  providers: [
    {
      provide: CATALOG_CLIENT,
      inject: [ConfigService],
      useFactory: (config: ConfigService) => {
        return new CatalogClient({
          BASE: config.getOrThrow<string>('app.stremhu-catalog-url'),
        });
      },
    },
    CatalogService,
  ],
  controllers: [CatalogController],
  exports: [CatalogService],
})
export class CatalogModule {}
