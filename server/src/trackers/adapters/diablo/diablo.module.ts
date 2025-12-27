import { Module } from '@nestjs/common';

import { TrackersCoreModule } from 'src/trackers/core/trackers-core.module';
import { TrackerEnum } from 'src/trackers/enum/tracker.enum';

import { TRACKER_TOKEN } from '../adapters.types';
import { DiabloAdapter } from './diablo.adapter';
import { DiabloClient } from './diablo.client';
import { DiabloClientFactory } from './diablo.client-factory';

@Module({
  imports: [TrackersCoreModule],
  providers: [
    { provide: TRACKER_TOKEN, useValue: TrackerEnum.DIABLO },
    DiabloAdapter,
    DiabloClient,
    DiabloClientFactory,
  ],
  exports: [DiabloAdapter],
})
export class DiabloModule {}
