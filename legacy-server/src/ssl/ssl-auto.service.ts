import { Injectable, Logger } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import * as acme from 'acme-client';
import { writeFile } from 'node:fs/promises';
import { join } from 'node:path';
import { setTimeout } from 'node:timers/promises';

import { safeReadFile } from 'src/common/utils/file.util';
import { DnsService } from 'src/dns/dns.service';

import { GeneratedCertificate } from './type/generated-certificate.type';
import { SslRequestCertificate } from './type/ssl-request-certificate.type';

@Injectable()
export class SslAutoService {
  private readonly logger = new Logger(SslAutoService.name);
  private readonly letsencryptDir: string;

  constructor(
    private readonly configService: ConfigService,
    private readonly dnsService: DnsService,
  ) {
    this.letsencryptDir = this.configService.getOrThrow<string>(
      'app.letsencrypt-dir',
    );
  }

  getPaths() {
    return {
      fullchain: join(this.letsencryptDir, 'fullchain.pem'),
      privkey: join(this.letsencryptDir, 'privkey.pem'),
      accountKey: join(this.letsencryptDir, 'account.key'),
    };
  }

  async generate(
    payload: SslRequestCertificate,
  ): Promise<GeneratedCertificate> {
    try {
      const { provider, host, email, token } = payload;

      const paths = this.getPaths();

      let accountKey: Buffer | null = await safeReadFile(paths.accountKey);

      if (!accountKey) {
        accountKey = await acme.crypto.createPrivateKey();
        await writeFile(paths.accountKey, accountKey);
      }

      const client = new acme.Client({
        directoryUrl: acme.directory.letsencrypt.staging,
        accountKey,
      });

      const [privkey, csr] = await acme.crypto.createCsr({
        commonName: host,
      });

      const fullchain = await client.auto({
        csr,
        email,
        termsOfServiceAgreed: true,
        challengePriority: ['dns-01'],
        challengeCreateFn: async (_authz, _challenge, keyAuthorization) => {
          await this.dnsService.update(provider, {
            host,
            token,
            txt: keyAuthorization,
          });

          await setTimeout(20_000);
        },
        challengeRemoveFn: async (_authz, _challenge, keyAuthorization) => {
          await this.dnsService.update(provider, {
            host,
            token,
            txt: keyAuthorization,
          });
        },
      });

      return {
        fullchain: Buffer.from(fullchain),
        privkey: Buffer.from(privkey),
      };
    } catch (error) {
      this.logger.error('🚨 Hiba történt a tanusítvány generálásakor!');
      throw error;
    }
  }
}
