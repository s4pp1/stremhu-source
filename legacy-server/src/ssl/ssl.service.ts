import { Injectable, Logger, OnModuleInit } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { X509Certificate } from 'node:crypto';
import { mkdir, writeFile } from 'node:fs/promises';
import { join } from 'node:path';

import { safeReadFile } from 'src/common/utils/file.util';
import { SettingsCoreService } from 'src/settings/core/settings-core.service';
import { NetworkModeEnum } from 'src/settings/enum/network-mode.enum';
import type { NetworkSettings } from 'src/settings/type/network-settings.type';

import { SslAutoService } from './ssl-auto.service';
import { SslSelfService } from './ssl-self.service';
import { GeneratedCertificate } from './type/generated-certificate.type';

@Injectable()
export class SslService implements OnModuleInit {
  private readonly logger = new Logger(SslService.name);
  private readonly letsencryptDir: string;

  constructor(
    private readonly configService: ConfigService,
    private readonly settingsCoreService: SettingsCoreService,
    private readonly sslSelfService: SslSelfService,
    private readonly sslAutoService: SslAutoService,
  ) {
    this.letsencryptDir = this.configService.getOrThrow<string>(
      'app.letsencrypt-dir',
    );
  }

  async onModuleInit() {
    await mkdir(this.letsencryptDir, { recursive: true });
  }

  getPaths() {
    return {
      fullchain: join(this.letsencryptDir, 'fullchain.pem'),
      privkey: join(this.letsencryptDir, 'privkey.pem'),
      accountKey: join(this.letsencryptDir, 'account.key'),
    };
  }

  async certificateBuffers(): Promise<GeneratedCertificate | null> {
    const paths = this.getPaths();

    const [fullchain, privkey] = await Promise.all([
      safeReadFile(paths.fullchain),
      safeReadFile(paths.privkey),
    ]);

    if (!fullchain || !privkey) {
      return null;
    }

    return { fullchain: fullchain, privkey: privkey };
  }

  async certificate(payload: NetworkSettings): Promise<GeneratedCertificate> {
    let certs = await this.certificateBuffers();

    if (certs === null) {
      if (payload.mode === NetworkModeEnum.MANUAL && !payload.reverseProxy) {
        throw new Error('⚠️ Nincs elérhető tanúsítvány!');
      }

      this.logger.warn('⚠️ A tanúsítvány nem található! Új generálása...');
      certs = await this.generateAndSaveCertificate(payload);
    }

    const { fullchain } = certs;

    const x509 = new X509Certificate(fullchain);
    const isHostValid = x509.checkHost(payload.host);

    if (!isHostValid) {
      if (payload.mode === NetworkModeEnum.MANUAL && !payload.reverseProxy) {
        throw new Error('⚠️ A tanúsítvány nem a megadott domain-hez tartozik!');
      }

      this.logger.warn(
        '⚠️ A tanúsítvány nem a domain-hez tartozik! Új generálása...',
      );
      certs = await this.generateAndSaveCertificate(payload);
    }

    const thirtyDaysInMs = 30 * 24 * 60 * 60 * 1000;
    const nowTime = new Date().getTime();
    const expiryTime = new Date(x509.validTo).getTime();

    if (expiryTime - nowTime < thirtyDaysInMs) {
      if (payload.mode === NetworkModeEnum.MANUAL && !payload.reverseProxy) {
        throw new Error('⚠️ A tanúsítvány lejárt!');
      }

      this.logger.warn('⚠️ A tanúsítvány hamarosan lejár! Új generálása...');
      certs = await this.generateAndSaveCertificate(payload);
    }

    return certs;
  }

  private async generateAndSaveCertificate(
    payload: NetworkSettings,
  ): Promise<GeneratedCertificate> {
    const certs = await this.generateCertificate(payload);
    const paths = this.getPaths();
    await Promise.all([
      writeFile(paths.fullchain, certs.fullchain),
      writeFile(paths.privkey, certs.privkey),
    ]);
    return certs;
  }

  private async generateCertificate(
    payload: NetworkSettings,
  ): Promise<GeneratedCertificate> {
    switch (payload.mode) {
      case NetworkModeEnum.LOCAL:
        return this.sslSelfService.generate(payload.host);
      case NetworkModeEnum.MANUAL:
        return this.sslSelfService.generate(payload.host);
      case NetworkModeEnum.AUTO:
        return this.sslAutoService.generate(payload);
    }
  }
}
