import { Injectable, Logger, OnModuleInit } from '@nestjs/common';
import _, { isEmpty } from 'lodash';
import { EntityManager } from 'typeorm';

import { CatalogService } from 'src/catalog/catalog.service';
import { GLOBAL_ID } from 'src/common/constant/common.constant';
import { LocalIpService } from 'src/local-ip/local-ip.service';
import { TorrentsService } from 'src/torrents/torrents.service';

import { SettingsStore } from './core/settings.store';
import { Setting } from './entity/setting.entity';
import { SettingToUpdate } from './settings.types';

@Injectable()
export class SettingsService implements OnModuleInit {
  private readonly logger = new Logger(SettingsService.name);

  constructor(
    private readonly settingsStore: SettingsStore,
    private readonly torrentsService: TorrentsService,
    private readonly localIpService: LocalIpService,
    private readonly catalogService: CatalogService,
  ) {}

  async onModuleInit() {
    await this.init();
  }

  async update(
    payload: SettingToUpdate,
    manager?: EntityManager,
  ): Promise<Setting> {
    const setting = await this.settingsStore.findOneOrThrow();

    // StremHU | Catalog token
    const { catalogToken } = payload;
    const tokenNotUndefined = !_.isUndefined(catalogToken);
    const tokenNotNull = catalogToken !== null;
    if (
      tokenNotUndefined &&
      tokenNotNull &&
      setting.catalogToken !== catalogToken
    ) {
      await this.catalogService.catalogHealthCheck(catalogToken);
    }

    // Torrent kliens
    if (
      payload.downloadLimit !== undefined ||
      payload.uploadLimit !== undefined ||
      payload.port !== undefined
    ) {
      await this.torrentsService.updateTorrentClient({
        downloadLimit: payload.downloadLimit,
        uploadLimit: payload.uploadLimit,
        port: payload.port,
      });
    }

    // Local IP vezérlés
    if (
      !_.isUndefined(payload.enebledlocalIp) &&
      setting.enebledlocalIp !== payload.enebledlocalIp
    ) {
      if (payload.enebledlocalIp) {
        await this.localIpService.enable();
      } else {
        await this.localIpService.disable();
      }
    }

    delete payload.port;

    if (!isEmpty(payload)) {
      const updatedSetting = await this.settingsStore.update(payload, manager);
      return updatedSetting;
    }

    return setting;
  }

  private async init() {
    const setting = await this.settingsStore.findOne();
    if (setting) return;

    this.logger.log('⚙️ Beállítások konfigurálása első indítással');

    await this.settingsStore.create({
      id: GLOBAL_ID,
      hitAndRun: true,
      enebledlocalIp: true,
      downloadLimit: -1,
      uploadLimit: -1,
      keepSeedSeconds: null,
      cacheRetentionSeconds: 14 * 24 * 60 * 60,
    });
  }
}
