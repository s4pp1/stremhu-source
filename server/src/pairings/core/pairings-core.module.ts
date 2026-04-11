import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';

import { Pairing } from '../entity/pairing.entity';
import { PairingsStore } from './pairings.store';

@Module({
  imports: [TypeOrmModule.forFeature([Pairing])],
  providers: [PairingsStore],
  exports: [PairingsStore],
})
export class PairingsCoreModule {}
