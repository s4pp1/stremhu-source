import { Module } from '@nestjs/common';

import { TrackersMetaService } from './trackers-meta.service';

@Module({
  imports: [],
  providers: [TrackersMetaService],
  controllers: [],
  exports: [TrackersMetaService],
})
export class TrackersMetaModule {}
