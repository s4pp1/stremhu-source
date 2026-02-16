import { Module } from '@nestjs/common';

import { TrackersMetaModule } from 'src/trackers/meta/trackers-meta.module';

import { PersistedTorrentsCoreModule } from './core/persisted-torrents-core.module';
import { PersistedTorrentsService } from './persisted-torrents.service';

@Module({
  imports: [PersistedTorrentsCoreModule, TrackersMetaModule],
  providers: [PersistedTorrentsService],
  controllers: [],
  exports: [PersistedTorrentsService],
})
export class PersistedTorrentsModule {}
