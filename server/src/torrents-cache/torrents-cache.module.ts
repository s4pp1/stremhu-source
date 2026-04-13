import { Module } from '@nestjs/common';

import { AuthModule } from 'src/auth/auth.module';
import { SettingsCoreModule } from 'src/settings/core/settings-core.module';
import { TorrentsModule } from 'src/torrents/torrents.module';

import { TorrentsCacheCoreModule } from './core/torrents-cache-core.module';
import { TorrentsCacheController } from './torrents-cache.controller';
import { TorrentsCacheService } from './torrents-cache.service';

@Module({
  imports: [
    AuthModule,
    TorrentsCacheCoreModule,
    SettingsCoreModule,
    TorrentsModule,
  ],
  providers: [TorrentsCacheService],
  exports: [TorrentsCacheService],
  controllers: [TorrentsCacheController],
})
export class TorrentsCacheModule {}
