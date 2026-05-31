import { Injectable, Logger } from '@nestjs/common';
import axios from 'axios';

import { NetworkProviderEnum } from 'src/settings/enum/network-provider.enum';

import { DNSUpdate } from '../type/dns-update.type';
import { DNSValidate } from '../type/dns-validate.type';
import { DnsProviderAdapter } from './dns-provider.types';

const BASE_URL = 'https://www.duckdns.org/update';

@Injectable()
export class DuckDnsAdapter implements DnsProviderAdapter {
  private readonly logger = new Logger(DuckDnsAdapter.name);
  readonly provider = NetworkProviderEnum.DUCKDNS;

  async validate(payload: DNSValidate): Promise<void> {
    const { host, token } = payload;

    const params = new URLSearchParams({
      domains: host,
      token: token,
    });

    const url = `${BASE_URL}?${params.toString()}`;

    const response = await axios.get(url, { timeout: 10_000 });

    if (!String(response.data).includes('OK')) {
      throw new Error(`DuckDNS validation failed: ${response.data}`);
    }
  }

  async update(payload: DNSUpdate): Promise<void> {
    const { ip, txt, host, token } = payload;

    if (txt) {
      const params = new URLSearchParams({
        domains: host,
        token,
        txt,
      });
      const response = await axios.get(`${BASE_URL}?${params.toString()}`);

      if (!String(response.data).includes('OK')) {
        throw new Error(`DuckDNS TXT update failed: ${response.data}`);
      }
    }

    if (ip) {
      const params = new URLSearchParams({
        domains: host,
        token,
        ip,
      });
      const url = `${BASE_URL}?${params.toString()}`;
      const response = await axios.get(url);

      if (!String(response.data).includes('OK')) {
        throw new Error(`DuckDNS IP update failed: ${response.data}`);
      }
    }
  }
}
