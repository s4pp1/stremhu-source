import { Module } from '@nestjs/common';

import { AuthModule } from 'src/auth/auth.module';
import { SettingsCoreModule } from 'src/settings/core/settings-core.module';
import { TorrentCacheCoreModule } from 'src/torrent-cache/core/torrent-cache-core.module';
import { UsersModule } from 'src/users/users.module';
import { WebTorrentModule } from 'src/web-torrent/web-torrent.module';

import { BithumenModule } from './adapters/bithumen/bithumen.module';
import { MajomparadeModule } from './adapters/majomparade/majomparade.module';
import { NcoreModule } from './adapters/ncore/ncore.module';
import { TrackerCredentialsModule } from './credentials/tracker-credentials.module';
import { TrackersController } from './trackers.controller';
import { TrackersService } from './trackers.service';

@Module({
  imports: [
    AuthModule,
    UsersModule,
    TrackerCredentialsModule,
    TorrentCacheCoreModule,
    WebTorrentModule,
    SettingsCoreModule,
    NcoreModule,
    BithumenModule,
    MajomparadeModule,
  ],
  providers: [TrackersService],
  controllers: [TrackersController],
  exports: [TrackersService],
})
export class TrackersModule {}
