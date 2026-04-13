import { Module } from '@nestjs/common';

import { SettingsModule } from 'src/settings/settings.module';

import { StremioCoreService } from './stremio-core.service';

@Module({
  imports: [SettingsModule],
  providers: [StremioCoreService],
  exports: [StremioCoreService],
})
export class StremioCoreModule {}
