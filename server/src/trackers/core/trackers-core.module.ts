import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';

import { TrackerCredential } from '../credentials/entity/tracker-credential.entity';
import { TrackersStore } from './trackers.store';

@Module({
  imports: [TypeOrmModule.forFeature([TrackerCredential])],
  providers: [TrackersStore],
  exports: [TrackersStore],
})
export class TrackersCoreModule {}
