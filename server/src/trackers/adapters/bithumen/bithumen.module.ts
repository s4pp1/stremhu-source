import { Module } from '@nestjs/common';

import { TrackerCredentialsModule } from 'src/trackers/credentials/tracker-credentials.module';
import { TrackerEnum } from 'src/trackers/enums/tracker.enum';

import { TRACKER_TOKEN } from '../adapters.types';
import { BithumenAdapter } from './bithumen.adapter';
import { BithumenClient } from './bithumen.client';
import { BithumenClientFactory } from './bithumen.client-factory';

@Module({
  imports: [TrackerCredentialsModule],
  providers: [
    { provide: TRACKER_TOKEN, useValue: TrackerEnum.BITHUMEN },
    BithumenAdapter,
    BithumenClient,
    BithumenClientFactory,
  ],
  exports: [BithumenAdapter],
})
export class BithumenModule {}
