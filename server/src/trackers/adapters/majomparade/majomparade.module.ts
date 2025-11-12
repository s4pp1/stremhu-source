import { Module } from '@nestjs/common';

import { TrackerCredentialsModule } from 'src/trackers/credentials/tracker-credentials.module';
import { TrackerEnum } from 'src/trackers/enums/tracker.enum';

import { TRACKER_TOKEN } from '../adapters.types';
import { MajomparadeAdapter } from './majomparade.adapter';
import { MajomparadeClient } from './majomparade.client';
import { MajomparadeClientFactory } from './majomparade.client-factory';

@Module({
  imports: [TrackerCredentialsModule],
  providers: [
    { provide: TRACKER_TOKEN, useValue: TrackerEnum.MAJOMPARADE },
    MajomparadeAdapter,
    MajomparadeClient,
    MajomparadeClientFactory,
  ],
  exports: [MajomparadeAdapter],
})
export class MajomparadeModule {}
