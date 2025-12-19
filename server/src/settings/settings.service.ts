import { Injectable, Logger, OnModuleInit } from '@nestjs/common';
import _ from 'lodash';
import { EntityManager } from 'typeorm';

import { CatalogService } from 'src/catalog/catalog.service';
import { GLOBAL_ID } from 'src/common/common.constant';
import { LocalIpService } from 'src/local-ip/local-ip.service';
import { TorrentCacheService } from 'src/torrent-cache/torrent-cache.service';
import { TorrentsService } from 'src/torrents/torrents.service';
import { TrackerMaintenanceService } from 'src/trackers/tracker-maintenance.service';

import { SettingsStore } from './core/settings.store';
import { Setting } from './entity/setting.entity';
import { SettingToUpdate } from './settings.types';

@Injectable()
export class SettingsService implements OnModuleInit {
  private readonly logger = new Logger(SettingsService.name);

  constructor(
    private readonly settingsStore: SettingsStore,
    private readonly trackerMaintenanceService: TrackerMaintenanceService,
    private readonly torrentsService: TorrentsService,
    private readonly localIpService: LocalIpService,
    private readonly torrentCacheService: TorrentCacheService,
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

    // Hit'n'Run Cron vezérlése
    if (
      !_.isUndefined(payload.hitAndRun) &&
      setting.hitAndRun !== payload.hitAndRun
    ) {
      await this.trackerMaintenanceService.setHitAndRunCron(payload.hitAndRun);
    }

    // Torrent Cache Cron vezérlése
    const hasCacheRetentionSeconds = !_.isUndefined(
      payload.cacheRetentionSeconds,
    );
    const prevState = _.isNumber(setting.cacheRetentionSeconds);
    const updateState = _.isNumber(payload.cacheRetentionSeconds);
    if (hasCacheRetentionSeconds && prevState !== updateState) {
      await this.torrentCacheService.setRetentionCleanupCron(updateState);
    }

    // Web Torrent letöltés/feltöltés beállítása
    const downloadLimit = payload.downloadLimit;
    const uploadLimit = payload.uploadLimit;

    if (
      (downloadLimit && setting.downloadLimit !== downloadLimit) ||
      (uploadLimit && uploadLimit !== setting.uploadLimit)
    ) {
      this.torrentsService.updateTorrentClient({
        downloadLimit: downloadLimit || setting.downloadLimit,
        uploadLimit: uploadLimit || setting.uploadLimit,
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

    const updatedSetting = await this.settingsStore.update(payload, manager);

    return updatedSetting;
  }

  private async init() {
    const setting = await this.settingsStore.findOne();
    if (setting) return;

    this.logger.log('⚙️ Beállítások konfigurálása első indítással');

    await this.settingsStore.create({
      id: GLOBAL_ID,
      hitAndRun: false,
      enebledlocalIp: true,
      downloadLimit: 12_500_000,
      uploadLimit: 12_500_000,
      cacheRetentionSeconds: 14 * 24 * 60 * 60,
    });
  }
}
