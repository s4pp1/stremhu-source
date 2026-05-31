import { BadRequestException, Injectable } from '@nestjs/common';

import { NetworkProviderEnum } from 'src/settings/enum/network-provider.enum';

import { DnsProviderAdapter } from './adapters/dns-provider.types';
import { DuckDnsAdapter } from './adapters/duckdns.adapter';
import { MyAddrAdapter } from './adapters/myaddr.adapter';

@Injectable()
export class DnsRegistry {
  private readonly adapters: Map<NetworkProviderEnum, DnsProviderAdapter>;

  constructor(duckdns: DuckDnsAdapter, myaddr: MyAddrAdapter) {
    this.adapters = new Map<NetworkProviderEnum, DnsProviderAdapter>([
      [duckdns.provider, duckdns],
      [myaddr.provider, myaddr],
    ]);
  }

  get(provider: NetworkProviderEnum): DnsProviderAdapter {
    const adapter = this.adapters.get(provider);
    if (!adapter) {
      throw new BadRequestException(
        `Nem regisztrált DNS szolgáltató: ${provider}`,
      );
    }
    return adapter;
  }
}
