import { Module } from '@nestjs/common';

import { SettingsCoreModule } from 'src/settings/core/settings-core.module';

import { WebTorrentService } from './webtorrent.service';

@Module({
  imports: [SettingsCoreModule],
  providers: [WebTorrentService],
  exports: [WebTorrentService],
})
export class WebTorrentModule {}
