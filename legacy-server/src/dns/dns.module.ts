import { Global, Module } from '@nestjs/common';
import { ConfigModule } from '@nestjs/config';

import { SettingsCoreModule } from 'src/settings/core/settings-core.module';

import { DuckDnsAdapter } from './adapters/duckdns.adapter';
import { MyAddrAdapter } from './adapters/myaddr.adapter';
import { DnsRegistry } from './dns.registry';
import { DnsService } from './dns.service';

@Global()
@Module({
  imports: [ConfigModule, SettingsCoreModule],
  providers: [DnsService, DnsRegistry, DuckDnsAdapter, MyAddrAdapter],
  exports: [DnsService],
})
export class DnsModule {}
