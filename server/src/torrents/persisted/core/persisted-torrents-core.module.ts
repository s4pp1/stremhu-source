import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';

import { PersistedTorrent } from '../entity/torrent.entity';
import { PersistedTorrentsStore } from './persisted-torrents.store';

@Module({
  imports: [TypeOrmModule.forFeature([PersistedTorrent])],
  providers: [PersistedTorrentsStore],
  exports: [PersistedTorrentsStore],
})
export class PersistedTorrentsCoreModule {}
