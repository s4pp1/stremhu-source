import { Module } from '@nestjs/common';

import { SettingsCoreModule } from '../core/settings-core.module';
import { AppSettingsService } from './app-settings.service';

@Module({
  imports: [SettingsCoreModule],
  providers: [AppSettingsService],
  exports: [AppSettingsService],
})
export class AppSettingsModule {}
