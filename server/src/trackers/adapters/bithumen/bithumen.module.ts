import { Module } from '@nestjs/common';

import { TrackersCoreModule } from 'src/trackers/core/trackers-core.module';
import { TrackerEnum } from 'src/trackers/enum/tracker.enum';

import { TRACKER_TOKEN } from '../adapters.types';
import { BithumenAdapter } from './bithumen.adapter';
import { BithumenClient } from './bithumen.client';
import { BithumenClientFactory } from './bithumen.client-factory';

@Module({
  imports: [TrackersCoreModule],
  providers: [
    { provide: TRACKER_TOKEN, useValue: TrackerEnum.BITHUMEN },
    BithumenAdapter,
    BithumenClient,
    BithumenClientFactory,
  ],
  exports: [BithumenAdapter],
})
export class BithumenModule {}
