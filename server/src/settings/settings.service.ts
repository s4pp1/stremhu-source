import { Injectable, Logger, OnModuleInit } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { internalIpV4 } from 'internal-ip';
import _ from 'lodash';
import { EntityManager } from 'typeorm';

import { GLOBAL_ID } from 'src/common/common.constant';
import { LocalIpService } from 'src/local-ip/local-ip.service';
import { TorrentCacheService } from 'src/torrent-cache/torrent-cache.service';
import { TrackersService } from 'src/trackers/trackers.service';
import { WebTorrentService } from 'src/web-torrent/web-torrent.service';

import { SettingsStore } from './core/settings.store';
import { Setting } from './entities/setting.entity';
import { SettingToUpdate } from './settings.types';

@Injectable()
export class SettingsService implements OnModuleInit {
  private readonly logger = new Logger(SettingsService.name);

  constructor(
    private configService: ConfigService,
    private settingsStore: SettingsStore,
    private trackersService: TrackersService,
    private webTorrentService: WebTorrentService,
    private localIpService: LocalIpService,
    private torrentCacheService: TorrentCacheService,
  ) {}

  async onModuleInit() {
    await this.init();
  }

  async update(
    payload: SettingToUpdate,
    manager?: EntityManager,
  ): Promise<Setting> {
    const setting = await this.settingsStore.findOneOrThrow();

    // Hit'n'Run Cron vezérlése
    if (
      !_.isUndefined(payload.hitAndRun) &&
      setting.hitAndRun !== payload.hitAndRun
    ) {
      await this.trackersService.setHitAndRunCron(payload.hitAndRun);
    }

    // Torrent Cache Cron vezérlése
    const hasCacheRetention = _.isUndefined(payload.cacheRetention);
    const prevState = _.isString(setting.cacheRetention);
    const updateState = _.isString(payload.cacheRetention);
    if (hasCacheRetention && prevState !== updateState) {
      await this.torrentCacheService.setRetentionCleanupCron(updateState);
    }

    // Web Torrent feltöltés beállítása
    if (
      !_.isUndefined(payload.uploadLimit) &&
      setting.uploadLimit !== payload.uploadLimit
    ) {
      this.webTorrentService.updateUploadLimit(payload.uploadLimit);
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

    const internalIp = (await internalIpV4()) ?? '127.0.0.1';
    const httpsPort = this.configService.getOrThrow<number>('app.https-port');
    const localIp = `https://${internalIp.split('.').join('-')}.local-ip.medicmobile.org:${httpsPort}`;

    await this.settingsStore.create({
      id: GLOBAL_ID,
      hitAndRun: false,
      enebledlocalIp: true,
      endpoint: localIp,
      uploadLimit: -1,
      cacheRetention: '14d',
    });
  }
}
