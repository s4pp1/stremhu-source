import { Module } from '@nestjs/common';

import { AuthModule } from 'src/auth/auth.module';
import { RelayCoreModule } from 'src/relay/core/relay-core.module';
import { SettingsCoreModule } from 'src/settings/core/settings-core.module';

import { RelaySettingsInternalController } from './relay-settings-internal.controller';

@Module({
  imports: [AuthModule, RelayCoreModule, SettingsCoreModule],
  controllers: [RelaySettingsInternalController],
})
export class RelaySettingsInternalModule {}
