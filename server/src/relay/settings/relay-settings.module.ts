import { Module } from '@nestjs/common';

import { RelaySettingsIntegrationModule } from './integration/relay-settings-integration.module';
import { RelaySettingsInternalModule } from './internal/relay-settings-internal.module';

@Module({
  imports: [RelaySettingsInternalModule, RelaySettingsIntegrationModule],
})
export class RelaySettingsModule {}
