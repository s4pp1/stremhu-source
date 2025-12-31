import { Module } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';

import { SettingsCoreModule } from 'src/settings/core/settings-core.module';

import { LibTorrentClient } from './client';
import { LIBTORRENT_CLIENT } from './libtorrent-client.token';
import { LibtorrentStreamService } from './libtorrent-stream.service';
import { LibtorrentService } from './libtorrent.service';

@Module({
  imports: [SettingsCoreModule],
  providers: [
    {
      provide: LIBTORRENT_CLIENT,
      inject: [ConfigService],
      useFactory: () => {
        return new LibTorrentClient({
          BASE: 'http://127.0.0.1:4300',
        });
      },
    },
    LibtorrentStreamService,
    LibtorrentService,
  ],
  exports: [LibtorrentService],
})
export class LibtorrentModule {}
