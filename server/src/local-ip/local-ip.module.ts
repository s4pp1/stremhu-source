import { Module } from '@nestjs/common';

import { AppSettingsModule } from 'src/settings/app/app-settings.module';

import { LocalIpService } from './local-ip.service';

@Module({
  imports: [AppSettingsModule],
  providers: [LocalIpService],
  exports: [LocalIpService],
})
export class LocalIpModule {}
