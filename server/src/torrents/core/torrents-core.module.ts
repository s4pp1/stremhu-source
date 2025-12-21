import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';

import { Torrent } from '../entity/torrent.entity';
import { TorrentsStore } from './torrents.store';

@Module({
  imports: [TypeOrmModule.forFeature([Torrent])],
  providers: [TorrentsStore],
  exports: [TorrentsStore],
})
export class TorrentsCoreModule {}
