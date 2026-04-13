import { Injectable, Logger } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { isUndefined, omitBy } from 'lodash';

import { AppSettingsSchema } from '../schema/app-settings.schema';
import { RelaySettingsSchema } from '../schema/relay-settings.schema';
import { APP_SETTINGS, TORRENT_SETTINGS } from '../settings.constant';
import { AppSettings } from '../type/app-settings.type';
import { RelaySettings } from '../type/relay-settings.type';
import { SettingsStore } from './settings.store';

@Injectable()
export class SettingsCoreService {
  private readonly logger = new Logger(SettingsCoreService.name);

  constructor(
    private readonly configService: ConfigService,
    private readonly settingsStore: SettingsStore,
  ) {}

  async appSettings(): Promise<AppSettings> {
    const settingRow = await this.settingsStore.findOneByKey(APP_SETTINGS);
    const setting = settingRow?.value ?? {};
    return AppSettingsSchema.parse(setting);
  }

  async updateAppSettings(payload: Partial<AppSettings>): Promise<AppSettings> {
    const current = await this.appSettings();

    const update = omitBy(payload, isUndefined);
    const merged = AppSettingsSchema.parse({ ...current, ...update });

    const entity = this.settingsStore.createEntity({
      key: APP_SETTINGS,
      value: merged,
    });

    await this.settingsStore.createOrUpdate(entity);

    return merged;
  }

  async relaySettings(): Promise<RelaySettings> {
    const settingRow = await this.settingsStore.findOneByKey(TORRENT_SETTINGS);
    const setting = settingRow?.value ?? {};
    return RelaySettingsSchema.parse(setting);
  }

  async updateRelaySettings(
    payload: Partial<RelaySettings>,
  ): Promise<RelaySettings> {
    const current = await this.relaySettings();

    const update = omitBy(payload, isUndefined);
    const merged = RelaySettingsSchema.parse({ ...current, ...update });

    const entity = this.settingsStore.createEntity({
      key: TORRENT_SETTINGS,
      value: merged,
    });

    await this.settingsStore.createOrUpdate(entity);

    return merged;
  }

  async getEndpoint() {
    const setting = await this.appSettings();

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
