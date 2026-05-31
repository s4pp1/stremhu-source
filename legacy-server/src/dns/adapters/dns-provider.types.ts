import { NetworkProviderEnum } from 'src/settings/enum/network-provider.enum';

import { DNSUpdate } from '../type/dns-update.type';
import { DNSValidate } from '../type/dns-validate.type';

export interface DnsProviderAdapter {
  provider: NetworkProviderEnum;

  validate(payload: DNSValidate): Promise<void>;

  update(payload: DNSUpdate): Promise<void>;
}
