import { Module } from '@nestjs/common';

import { AuthModule } from 'src/auth/auth.module';
import { TorrentsCacheCoreModule } from 'src/torrents-cache/core/torrents-cache-core.module';
import { TrackersModule } from 'src/trackers/trackers.module';
import { UsersModule } from 'src/users/users.module';

import { StremioCatalogsController } from './stremio-catalogs.controller';
import { StremioCatalogsService } from './stremio-catalogs.service';

@Module({
  imports: [AuthModule, UsersModule, TrackersModule, TorrentsCacheCoreModule],
  controllers: [StremioCatalogsController],
  providers: [StremioCatalogsService],
})
export class StremioCatalogsModule {}
