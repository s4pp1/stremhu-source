import { Injectable, Logger } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { join } from 'node:path';
import selfsigned from 'selfsigned';

import { GeneratedCertificate } from './type/generated-certificate.type';

@Injectable()
export class SslSelfService {
  private readonly logger = new Logger(SslSelfService.name);
  private readonly letsencryptDir: string;

  constructor(private readonly configService: ConfigService) {
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

  async generate(localIp: string): Promise<GeneratedCertificate> {
    try {
      const attrs = [{ name: 'commonName', value: localIp }];
      const pems = await selfsigned.generate(attrs, {
        extensions: [
          {
            name: 'subjectAltName',
            altNames: [
              {
                type: 7,
                ip: localIp,
              },
            ],
          },
        ],
      });

      return {
        fullchain: Buffer.from(pems.cert),
        privkey: Buffer.from(pems.private),
      };
    } catch (error) {
      this.logger.error('🚨 Hiba történt a tanusítvány generálásakor!');
      throw error;
    }
  }
}
