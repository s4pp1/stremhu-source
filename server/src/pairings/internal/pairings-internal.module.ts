import { Module } from '@nestjs/common';

import { AuthModule } from 'src/auth/auth.module';

import { PairingsCoreModule } from '../core/pairings-core.module';
import { PairingsInternalController } from './pairings-internal.controller';

@Module({
  imports: [AuthModule, PairingsCoreModule],
  controllers: [PairingsInternalController],
})
export class PairingsInternalModule {}
