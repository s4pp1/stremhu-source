import { NetworkProviderEnum } from 'src/settings/enum/network-provider.enum';

export type SslRequestCertificate = {
  provider: NetworkProviderEnum;
  email: string;
  token: string;
  host: string;
};
