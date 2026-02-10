import { Module } from '@nestjs/common';

import { PersistedTorrentsCoreModule } from './core/persisted-torrents-core.module';
import { PersistedTorrentsService } from './persisted-torrents.service';

@Module({
  imports: [PersistedTorrentsCoreModule],
  providers: [PersistedTorrentsService],
  controllers: [],
  exports: [PersistedTorrentsService],
})
export class PersistedTorrentsModule {}
