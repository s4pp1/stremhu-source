import { Module } from '@nestjs/common';

import { TorrentsCacheStore } from './torrents-cache.store';

@Module({
  providers: [TorrentsCacheStore],
  exports: [TorrentsCacheStore],
})
export class TorrentsCacheCoreModule {}
