import { Module } from '@nestjs/common';

import { AuthModule } from 'src/auth/auth.module';

import { PairingsCoreModule } from './core/pairings-core.module';
import { PairingsController } from './pairings.controller';
import { PairingsService } from './pairings.service';

@Module({
  imports: [AuthModule, PairingsCoreModule],
  providers: [PairingsService],
  controllers: [PairingsController],
  exports: [PairingsService],
})
export class PairingsModule {}
