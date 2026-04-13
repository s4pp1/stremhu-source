import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';

import { Pairing } from '../entity/pairing.entity';
import { PairingsCoreService } from './pairings-core.service';
import { PairingsStore } from './pairings.store';

@Module({
  imports: [TypeOrmModule.forFeature([Pairing])],
  providers: [PairingsStore, PairingsCoreService],
  exports: [PairingsCoreService],
})
export class PairingsCoreModule {}
