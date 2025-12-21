import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';

import { Tracker } from '../entity/tracker.entity';
import { TrackersStore } from './trackers.store';

@Module({
  imports: [TypeOrmModule.forFeature([Tracker])],
  providers: [TrackersStore],
  exports: [TrackersStore],
})
export class TrackersCoreModule {}
