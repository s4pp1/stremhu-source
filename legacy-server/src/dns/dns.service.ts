import { Injectable, Logger } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { Cron, CronExpression } from '@nestjs/schedule';
import axios from 'axios';

import { SettingsCoreService } from 'src/settings/core/settings-core.service';
import { NetworkConnectionEnum } from 'src/settings/enum/network-connection.enum';
import { NetworkModeEnum } from 'src/settings/enum/network-mode.enum';
import { NetworkProviderEnum } from 'src/settings/enum/network-provider.enum';

import { DnsRegistry } from './dns.registry';
import { DNSUpdate } from './type/dns-update.type';
import { DNSValidate } from './type/dns-validate.type';

@Injectable()
export class DnsService {
  private readonly logger = new Logger(DnsService.name);

  constructor(
    private readonly registry: DnsRegistry,
    private readonly configService: ConfigService,
    private readonly settingsCoreService: SettingsCoreService,
  ) {}

  async validate(
    provider: NetworkProviderEnum,
    payload: DNSValidate,
  ): Promise<void> {
    const adapter = this.registry.get(provider);
    await adapter.validate(payload);
  }

  async update(
    provider: NetworkProviderEnum,
    payload: DNSUpdate,
  ): Promise<void> {
    const adapter = this.registry.get(provider);
    await adapter.update(payload);
  }

  async getPublicIp(): Promise<string> {
    try {
      const response = await axios.get<string>('https://api.ipify.org');
      return response.data;
    } catch (error) {
      this.logger.error(`Failed to fetch public IP: ${error}`);
      throw error;
    }
  }

  async getCurrentIp(mode: NetworkConnectionEnum): Promise<string> {
    if (mode === NetworkConnectionEnum.LOCAL) {
      return this.configService.getOrThrow<string>('app.internal-ip');
    }
    return this.getPublicIp();
  }

  @Cron(CronExpression.EVERY_5_MINUTES)
  async syncIp() {
    const networkSettings =
      await this.settingsCoreService.networkSettingsOrThrow();

    if (networkSettings.mode !== NetworkModeEnum.AUTO) return;

    try {
      const currentIp = await this.getCurrentIp(networkSettings.connection);

      if (networkSettings.ip !== currentIp) {
        this.logger.log(
          `IP change detected (${networkSettings.ip} -> ${currentIp}). Updating DNS...`,
        );

        await this.update(networkSettings.provider, {
          host: networkSettings.host,
          token: networkSettings.token,
          ip: currentIp,
        });

        await this.settingsCoreService.updateNetworkSettings({
          provider: networkSettings.provider,
          ip: currentIp,
        });
      }
    } catch (error) {
      this.logger.error(`IP sync failed: ${error}`);
    }
  }
}
