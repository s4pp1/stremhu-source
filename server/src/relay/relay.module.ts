import { Module } from '@nestjs/common';

import { SettingsCoreModule } from 'src/settings/core/settings-core.module';

import { RelayCoreModule } from './core/relay-core.module';
import { RelaySettingsModule } from './settings/relay-settings.module';

@Module({
  imports: [RelayCoreModule, SettingsCoreModule, RelaySettingsModule],
})
export class RelayModule {}
