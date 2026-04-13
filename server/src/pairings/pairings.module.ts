import { Module } from '@nestjs/common';

import { PairingsCoreModule } from './core/pairings-core.module';
import { PairingsIntegrationModule } from './integration/pairings-integration.module';
import { PairingsInternalModule } from './internal/pairings-internal.module';

@Module({
  imports: [
    PairingsCoreModule,
    PairingsInternalModule,
    PairingsIntegrationModule,
  ],
})
export class PairingsModule {}
