import { Module } from '@nestjs/common';

import { SettingsCoreModule } from 'src/settings/core/settings-core.module';
import { TorrentsModule } from 'src/torrents/torrents.module';

import { TorrentCacheCoreModule } from './core/torrent-cache-core.module';
import { TorrentCacheService } from './torrent-cache.service';

@Module({
  imports: [TorrentCacheCoreModule, SettingsCoreModule, TorrentsModule],
  providers: [TorrentCacheService],
  exports: [TorrentCacheService],
})
export class TorrentCacheModule {}
