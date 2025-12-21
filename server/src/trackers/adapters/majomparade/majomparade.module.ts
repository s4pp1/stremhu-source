import { Module } from '@nestjs/common';

import { TrackersCoreModule } from 'src/trackers/core/trackers-core.module';
import { TrackerEnum } from 'src/trackers/enum/tracker.enum';

import { TRACKER_TOKEN } from '../adapters.types';
import { MajomparadeAdapter } from './majomparade.adapter';
import { MajomparadeClient } from './majomparade.client';
import { MajomparadeClientFactory } from './majomparade.client-factory';

@Module({
  imports: [TrackersCoreModule],
  providers: [
    { provide: TRACKER_TOKEN, useValue: TrackerEnum.MAJOMPARADE },
    MajomparadeAdapter,
    MajomparadeClient,
    MajomparadeClientFactory,
  ],
  exports: [MajomparadeAdapter],
})
export class MajomparadeModule {}
