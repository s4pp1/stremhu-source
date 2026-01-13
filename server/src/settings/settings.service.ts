import { Injectable, Logger, OnModuleInit } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';

import { CatalogService } from 'src/catalog/catalog.service';
import { LocalIpService } from 'src/local-ip/local-ip.service';

import { AppSettings, AppSettingsService } from './app/app-settings.service';
import { RelaySettingsService } from './relay/relay-settings.service';

@Injectable()
export class SettingsService implements OnModuleInit {
  private readonly logger = new Logger(SettingsService.name);

  constructor(
    private readonly configService: ConfigService,
    private readonly appSettingsService: AppSettingsService,
    private readonly relaySettingsService: RelaySettingsService,
    private readonly catalogService: CatalogService,
    private readonly localIpService: LocalIpService,
  ) {}

  async onModuleInit() {
    this.logger.log('⚙️ Konfigurációk inicializálása és szinkronizálása...');

    const port = this.configService.getOrThrow<number>('torrent.port');

    try {
      await Promise.all([
        this.appSettingsService.update({}),
        this.relaySettingsService.update({ port }),
      ]);
    } catch (error) {
      this.logger.fatal(
        '🚨 Hiba történt a konfigurációk inicializálása közben!',
        error,
      );
    }
  }

  async update(payload: Partial<AppSettings>): Promise<AppSettings> {
    const current = await this.appSettingsService.get();
    const updated = await this.appSettingsService.update(payload);

    // StremHU Catalog token frissítése
    if (
      updated.catalogToken !== null &&
      updated.catalogToken !== current.catalogToken
    ) {
      await this.catalogService.catalogHealthCheck(updated.catalogToken);
    }

    // Local IP elindítása / leállítása
    if (updated.enebledlocalIp) {
      await this.localIpService.enable();
    } else {
      await this.localIpService.disable();
    }

    return updated;
  }

  async getEndpoint() {
    const setting = await this.appSettingsService.get();

    let endpoint = this.buildLocalUrl('127.0.0.1');

    if (setting.enebledlocalIp && setting.address) {
      endpoint = this.buildLocalUrl(setting.address);
    }

    if (!setting.enebledlocalIp && setting.address) {
      endpoint = setting.address;
    }

    return endpoint;
  }

  buildLocalUrl(ipAddress: string) {
    const httpsPort = this.configService.getOrThrow<number>('app.https-port');
    return `https://${ipAddress.split('.').join('-')}.local-ip.medicmobile.org:${httpsPort}`;
  }
}
