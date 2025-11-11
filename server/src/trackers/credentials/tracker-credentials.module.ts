import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';

import { WebTorrentModule } from 'src/web-torrent/web-torrent.module';

import { TrackerCredential } from './entities/tracker-credential.entity';
import { TrackerCredentialsService } from './tracker-credentials.service';

@Module({
  imports: [TypeOrmModule.forFeature([TrackerCredential]), WebTorrentModule],
  providers: [TrackerCredentialsService],
  exports: [TrackerCredentialsService],
})
export class TrackerCredentialsModule {}
