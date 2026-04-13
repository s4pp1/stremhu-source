import { Module } from '@nestjs/common';

import { AuthModule } from 'src/auth/auth.module';
import { RelayCoreModule } from 'src/relay/core/relay-core.module';
import { SettingsCoreModule } from 'src/settings/core/settings-core.module';

import { RelaySettingsIntegrationController } from './relay-settings-integration.controller';

@Module({
  imports: [AuthModule, RelayCoreModule, SettingsCoreModule],
  controllers: [RelaySettingsIntegrationController],
})
export class RelaySettingsIntegrationModule {}
