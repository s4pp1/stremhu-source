import { Module } from '@nestjs/common';

import { TrackersCoreModule } from 'src/trackers/core/trackers-core.module';
import { TrackerEnum } from 'src/trackers/enum/tracker.enum';

import { TRACKER_TOKEN } from '../adapters.types';
import { NcoreAdapter } from './ncore.adapter';
import { NcoreClient } from './ncore.client';
import { NcoreClientFactory } from './ncore.client-factory';

@Module({
  imports: [TrackersCoreModule],
  providers: [
    { provide: TRACKER_TOKEN, useValue: TrackerEnum.NCORE },
    NcoreAdapter,
    NcoreClient,
    NcoreClientFactory,
  ],
  exports: [NcoreAdapter],
})
export class NcoreModule {}
