import { Module } from '@nestjs/common';

import { TrackerCredentialsModule } from 'src/trackers/credentials/tracker-credentials.module';
import { TrackerEnum } from 'src/trackers/enums/tracker.enum';

import { TRACKER_TOKEN } from '../adapters.types';
import { NcoreAdapter } from './ncore.adapter';
import { NcoreClient } from './ncore.client';
import { NcoreClientFactory } from './ncore.client-factory';

@Module({
  imports: [TrackerCredentialsModule],
  providers: [
    { provide: TRACKER_TOKEN, useValue: TrackerEnum.NCORE },
    NcoreAdapter,
    NcoreClient,
    NcoreClientFactory,
  ],
  exports: [NcoreAdapter],
})
export class NcoreModule {}
