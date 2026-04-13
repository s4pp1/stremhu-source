import { Injectable, Logger, OnModuleInit } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';

import { CatalogService } from 'src/catalog/catalog.service';
import { LocalIpService } from 'src/local-ip/local-ip.service';

import { SettingsCoreService } from '../core/settings-core.service';
import { AppSettings } from '../type/app-settings.type';

@Injectable()
export class SettingsSyncService implements OnModuleInit {
  private readonly logger = new Logger(SettingsSyncService.name);

  constructor(
    private readonly configService: ConfigService,
    private readonly settingsCoreService: SettingsCoreService,
    private readonly catalogService: CatalogService,
    private readonly localIpService: LocalIpService,
  ) {}

  async onModuleInit() {
    this.logger.log('⚙️ Konfigurációk inicializálása és szinkronizálása...');

    const port = this.configService.getOrThrow<number>('torrent.port');

    try {
      await Promise.all([
        this.settingsCoreService.updateAppSettings({}),
        this.settingsCoreService.updateRelaySettings({ port }),
      ]);
    } catch (error) {
      this.logger.fatal(
        '🚨 Hiba történt a konfigurációk inicializálása közben!',
        error,
      );
    }
  }

  async update(payload: Partial<AppSettings>): Promise<AppSettings> {
    const current = await this.settingsCoreService.appSettings();
    const updated = await this.settingsCoreService.updateAppSettings(payload);

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
}
