import { Module } from '@nestjs/common';

import { RelayRuntimeCoreService } from './relay-core-runtime.service';
import { RelayCoreService } from './relay-core.service';

@Module({
  providers: [RelayCoreService, RelayRuntimeCoreService],
  exports: [RelayCoreService, RelayRuntimeCoreService],
})
export class RelayCoreModule {}
