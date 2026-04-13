import { Module } from '@nestjs/common';

import { SettingsCoreModule } from 'src/settings/core/settings-core.module';

import { StremioCoreService } from './stremio-core.service';

@Module({
  imports: [SettingsCoreModule],
  providers: [StremioCoreService],
  exports: [StremioCoreService],
})
export class StremioCoreModule {}
