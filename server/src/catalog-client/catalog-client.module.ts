import { Module } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';

import { SettingsCoreModule } from 'src/settings/core/settings-core.module';

import { CatalogClientService } from './catalog-client.service';
import { CATALOG_CLIENT } from './catalog-client.token';
import { CatalogClient } from './client';

@Module({
  imports: [SettingsCoreModule],
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
    CatalogClientService,
  ],
  exports: [CatalogClientService],
})
export class CatalogClientModule {}
