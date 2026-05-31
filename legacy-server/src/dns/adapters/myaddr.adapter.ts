import { Injectable, Logger } from '@nestjs/common';
import axios from 'axios';

import { NetworkProviderEnum } from 'src/settings/enum/network-provider.enum';

import { DNSUpdate } from '../type/dns-update.type';
import { DNSValidate } from '../type/dns-validate.type';
import { DnsProviderAdapter } from './dns-provider.types';

const BASE_URL = 'https://myaddr.tools/update';

@Injectable()
export class MyAddrAdapter implements DnsProviderAdapter {
  private readonly logger = new Logger(MyAddrAdapter.name);
  readonly provider = NetworkProviderEnum.MYADDR;

  async validate(payload: DNSValidate): Promise<void> {
    const { token } = payload;

    const params = new URLSearchParams({ key: token });
    const url = `${BASE_URL}?${params.toString()}`;

    const response = await axios.get(url, { timeout: 10_000 });

    if (!String(response.data).includes('OK')) {
      throw new Error(`MyAddr validation failed: ${response.data}`);
    }
  }

  async update(payload: DNSUpdate): Promise<void> {
    const { ip, txt, token } = payload;

    if (txt) {
      const params = new URLSearchParams({
        key: token,
        acme_challenge: txt,
      });

      const url = `${BASE_URL}?${params.toString()}`;
      const response = await axios.get(url);
      if (!String(response.data).includes('OK')) {
        throw new Error(`MyAddr update failed: ${response.data}`);
      }
    }

    if (ip) {
      const params = new URLSearchParams({
        key: token,
        ip,
      });

      const url = `${BASE_URL}?${params.toString()}`;
      const response = await axios.get(url);
      if (!String(response.data).includes('OK')) {
        throw new Error(`MyAddr update failed: ${response.data}`);
      }
    }
  }
}
