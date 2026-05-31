import { Global, Module } from '@nestjs/common';
import { ConfigModule } from '@nestjs/config';

import { DnsModule } from 'src/dns/dns.module';
import { SettingsCoreModule } from 'src/settings/core/settings-core.module';

import { SslAutoService } from './ssl-auto.service';
import { SslSelfService } from './ssl-self.service';
import { SslService } from './ssl.service';

@Global()
@Module({
  imports: [ConfigModule, SettingsCoreModule, DnsModule],
  providers: [SslService, SslSelfService, SslAutoService],
  exports: [SslService],
})
export class SslModule {}
