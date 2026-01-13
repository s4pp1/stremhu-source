import { Module } from '@nestjs/common';

import { SettingsCoreModule } from '../core/settings-core.module';
import { RelaySettingsService } from './relay-settings.service';

@Module({
  imports: [SettingsCoreModule],
  providers: [RelaySettingsService],
  exports: [RelaySettingsService],
})
export class RelaySettingsModule {}
