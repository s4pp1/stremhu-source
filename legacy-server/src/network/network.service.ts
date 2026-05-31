import {
  BadRequestException,
  Injectable,
  Logger,
  OnModuleInit,
} from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import axios from 'axios';
import * as https from 'node:https';
import { setTimeout } from 'node:timers/promises';

import { DnsService } from 'src/dns/dns.service';
import { ServerService } from 'src/server/server.service';
import { SettingsCoreService } from 'src/settings/core/settings-core.service';
import { NetworkModeEnum } from 'src/settings/enum/network-mode.enum';
import {
  NetworkLocalSettings,
  NetworkSettings,
} from 'src/settings/type/network-settings.type';
import { SslService } from 'src/ssl/ssl.service';

import { NetworkAutoSetupDto } from './dto/network-setup.dto';
import { NetworkSetupModeEnum } from './enum/network-setup-mode.enum';
import { NetworkSetup } from './type/network-setup.type';

@Injectable()
export class NetworkService implements OnModuleInit {
  private readonly logger = new Logger(NetworkService.name);
  private readonly internalIp: string;
  private readonly port: number;

  private inProgress = false;

  constructor(
    private readonly configService: ConfigService,
    private readonly sslService: SslService,
    private readonly dnsService: DnsService,
    private readonly serverService: ServerService,
    private readonly settingsCoreService: SettingsCoreService,
  ) {
    this.internalIp = this.configService.getOrThrow<string>('app.internal-ip');
    this.port = this.configService.getOrThrow<number>('app.port');
  }

  async onModuleInit() {
    const networkSettings = await this.settingsCoreService.networkSettings();

    if (!networkSettings) {
      await this.setupLocal();
    }
  }

  async setupLocal(): Promise<NetworkSettings> {
    const networkSettings: NetworkLocalSettings = {
      mode: NetworkModeEnum.LOCAL,
      host: this.internalIp,
      ip: this.internalIp,
    };

    await this.sslService.certificate(networkSettings);
    return this.settingsCoreService.updateNetworkSettings(networkSettings);
  }

  async verifyInternalConnectivity() {
    const networkSettings: NetworkLocalSettings = {
      mode: NetworkModeEnum.LOCAL,
      host: this.internalIp,
      ip: this.internalIp,
    };

    const isConnected = await this.checkConnectivity(networkSettings, 0);

    if (!isConnected) {
      this.logger.fatal(
        `❗❗❗ A "${this.internalIp}" címen nem érhető el a szerver! A docker-compose.yml konfigurációban módosítsd a INTERNAL_IP-t a szerver IP hálózati címére! ❗❗❗`,
      );
      process.exit(1);
    }
  }

  get() {
    return;
  }

  async setup(payload: NetworkSetup) {
    try {
      this.inProgress = true;

      let networkSettings: NetworkSettings;

      if (payload.mode === NetworkSetupModeEnum.MANUAL) {
        networkSettings = {
          mode: NetworkModeEnum.MANUAL,
          host: payload.host,
          reverseProxy: payload.reverseProxy,
        };
      } else {
        const ip = await this.dnsService.getCurrentIp(payload.connection);

        networkSettings = {
          mode: NetworkModeEnum.AUTO,
          host: payload.host,
          connection: payload.connection,
          provider: payload.provider,
          email: payload.email,
          ip,
          token: payload.token,
        };
      }

      switch (payload.mode) {
        case NetworkSetupModeEnum.MANUAL: {
          const isConnected = await this.checkConnectivity(networkSettings);
          if (!isConnected) {
            throw new BadRequestException('⚠️ A szerver nem elérhető!');
          }

          await this.settingsCoreService.updateNetworkSettings(networkSettings);

          void this.triggerRestart();

          return;
        }
        case NetworkSetupModeEnum.AUTO: {
          await this.dnsValidateCredentials(payload);

          await this.dnsIpSync(payload);

          await this.checkConnectionWithFallback(networkSettings);

          await this.sslService.certificate(networkSettings);

          await this.settingsCoreService.updateNetworkSettings(networkSettings);

          void this.triggerRestart();

          return;
        }
      }
    } catch (err) {
      throw new BadRequestException(err);
    } finally {
      this.inProgress = false;
    }
  }

  private async dnsValidateCredentials(payload: NetworkAutoSetupDto) {
    await this.dnsService.validate(payload.provider, {
      host: payload.host,
      token: payload.token,
    });
  }

  private async dnsIpSync(payload: NetworkAutoSetupDto): Promise<string> {
    const ip = await this.dnsService.getCurrentIp(payload.connection);

    await this.dnsService.update(payload.provider, {
      host: payload.host,
      token: payload.token,
      ip,
    });

    return ip;
  }

  private async checkConnectionWithFallback(networkSettings: NetworkSettings) {
    const isConnected = await this.checkConnectivity(networkSettings);

    const currentNetworkSettings =
      await this.settingsCoreService.networkSettingsOrThrow();

    if (!isConnected) {
      if (currentNetworkSettings.mode === NetworkModeEnum.AUTO) {
        await this.dnsService.update(currentNetworkSettings.provider, {
          host: currentNetworkSettings.host,
          token: currentNetworkSettings.token,
          ip: currentNetworkSettings.ip,
        });
      }

      throw new Error(
        'A szerver nem érhető el a megadott domainen keresztül. A DNS-t visszaállítottuk. Ellenőrizd a port forward-ot!',
      );
    }
  }

  private async checkConnectivity(
    networkSettings: NetworkSettings,
    retry = 6,
  ): Promise<boolean> {
    let useReverseProxy = false;
    if (
      networkSettings.mode === NetworkModeEnum.MANUAL &&
      networkSettings.reverseProxy
    ) {
      useReverseProxy = true;
    }

    let port: number | undefined = this.port;
    if (useReverseProxy) {
      port = undefined;
    }

    const url = `https://${networkSettings.host}${port ? `:${port}` : ''}/api/health`;

    const httpsAgent = new https.Agent({
      rejectUnauthorized: false,
    });

    for (let retryCount = 0; retryCount <= retry; retryCount++) {
      try {
        await axios.get(url, {
          timeout: 2_000,
          httpsAgent,
        });
        return true;
      } catch {
        if (retryCount === retry) return false;
        await setTimeout(10_000);
      }
    }

    return false;
  }

  private async triggerRestart() {
    await setTimeout(2_000);

    try {
      void this.serverService.restart();
    } catch (error) {
      this.logger.error(`Automatic restart failed: ${error}`);
    }
  }
}
