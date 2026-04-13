import { Module } from '@nestjs/common';

import { TorrentsCacheCoreModule } from 'src/torrents-cache/core/torrents-cache-core.module';
import { TrackersModule } from 'src/trackers/trackers.module';

import { StremioCatalogsCoreService } from './stremio-catalogs-core.service';

@Module({
  imports: [TrackersModule, TorrentsCacheCoreModule],
  providers: [StremioCatalogsCoreService],
  exports: [StremioCatalogsCoreService],
})
export class StremioCatalogsCoreModule {}
