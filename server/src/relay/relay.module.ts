import { Module } from '@nestjs/common';

import { SettingsCoreModule } from 'src/settings/core/settings-core.module';

import { RelayCoreModule } from './core/relay-core.module';

@Module({
  imports: [RelayCoreModule, SettingsCoreModule],
})
export class RelayModule {}
