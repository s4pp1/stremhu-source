import { Module } from '@nestjs/common';

import { PairingsCoreModule } from '../core/pairings-core.module';
import { PairingsIntegrationController } from './pairings-integration.controller';

@Module({
  imports: [PairingsCoreModule],
  controllers: [PairingsIntegrationController],
})
export class PairingsIntegrationModule {}
