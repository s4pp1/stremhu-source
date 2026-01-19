import { Module } from '@nestjs/common';

import { AuthModule } from 'src/auth/auth.module';
import { CatalogModule } from 'src/catalog/catalog.module';
import { LocalIpModule } from 'src/local-ip/local-ip.module';

import { AppSettingsModule } from './app/app-settings.module';
import { SettingsCoreModule } from './core/settings-core.module';
import { RelaySettingsModule } from './relay/relay-settings.module';
import { SettingsController } from './settings.controller';
import { SettingsService } from './settings.service';

@Module({
  imports: [
    AuthModule,
    SettingsCoreModule,
    AppSettingsModule,
    RelaySettingsModule,
    LocalIpModule,
    CatalogModule,
  ],
  providers: [SettingsService],
  controllers: [SettingsController],
  exports: [SettingsService],
})
export class SettingsModule {}
