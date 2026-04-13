import { Module } from '@nestjs/common';

import { AuthModule } from 'src/auth/auth.module';

import { SettingsCoreModule } from './core/settings-core.module';
import { SettingsController } from './settings.controller';
import { SettingsSyncModule } from './sync/settings-sync.module';

@Module({
  imports: [AuthModule, SettingsCoreModule, SettingsSyncModule],
  controllers: [SettingsController],
})
export class SettingsModule {}
