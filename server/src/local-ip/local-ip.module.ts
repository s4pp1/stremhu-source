import { Module } from '@nestjs/common';

import { SettingsCoreModule } from 'src/settings/core/settings-core.module';

import { LocalIpService } from './local-ip.service';

@Module({
  imports: [SettingsCoreModule],
  providers: [LocalIpService],
  exports: [LocalIpService],
})
export class LocalIpModule {}
