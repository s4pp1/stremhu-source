import { Module } from '@nestjs/common';

import { TrackersCoreModule } from 'src/trackers/core/trackers-core.module';
import { TrackerEnum } from 'src/trackers/enum/tracker.enum';

import { TRACKER_TOKEN } from '../adapters.types';
import { InsaneAdapter } from './insane.adapter';
import { InsaneClient } from './insane.client';
import { InsaneClientFactory } from './insane.client-factory';

@Module({
  imports: [TrackersCoreModule],
  providers: [
    { provide: TRACKER_TOKEN, useValue: TrackerEnum.INSANE },
    InsaneAdapter,
    InsaneClient,
    InsaneClientFactory,
  ],
  exports: [InsaneAdapter],
})
export class InsaneModule {}
