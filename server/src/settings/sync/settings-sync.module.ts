import { Module } from '@nestjs/common';

import { CatalogModule } from 'src/catalog/catalog.module';
import { LocalIpModule } from 'src/local-ip/local-ip.module';

import { SettingsCoreModule } from '../core/settings-core.module';
import { SettingsSyncService } from './settings-sync.service';

@Module({
  imports: [SettingsCoreModule, LocalIpModule, CatalogModule],
  providers: [SettingsSyncService],
  exports: [SettingsSyncService],
})
export class SettingsSyncModule {}
