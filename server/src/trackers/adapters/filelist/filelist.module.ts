import { Module } from '@nestjs/common';

import { TrackersCoreModule } from 'src/trackers/core/trackers-core.module';
import { TrackerEnum } from 'src/trackers/enum/tracker.enum';

import { TRACKER_TOKEN } from '../adapters.types';
import { FilelistAdapter } from './filelist.adapter';
import { FilelistClient } from './filelist.client';
import { FilelistClientFactory } from './filelist.client-factory';

@Module({
  imports: [TrackersCoreModule],
  providers: [
    { provide: TRACKER_TOKEN, useValue: TrackerEnum.FILELIST },
    FilelistAdapter,
    FilelistClient,
    FilelistClientFactory,
  ],
  exports: [FilelistAdapter],
})
export class FilelistModule {}
