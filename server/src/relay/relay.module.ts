import { Module } from '@nestjs/common';

import { RelaySettingsModule } from 'src/settings/relay/relay-settings.module';

import { RelayRuntimeService } from './relay-runtime.service';
import { RelayService } from './relay.service';

@Module({
  imports: [RelaySettingsModule],
  providers: [RelayRuntimeService, RelayService],
  exports: [RelayService, RelayRuntimeService],
})
export class RelayModule {}
