import { Injectable, Logger, OnApplicationBootstrap } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { Cron, CronExpression, SchedulerRegistry } from '@nestjs/schedule';
import axios from 'axios';
import axiosRetry, { exponentialDelay } from 'axios-retry';
import * as https from 'node:https';
import { z } from 'zod';

import { AppSettingsService } from 'src/settings/app/app-settings.service';

import { EXPRESS } from '../main';
import { LOCAL_IP_CRON_JOB, LOCAL_IP_KEYS_URL } from './local-ip.constants';

const localIpSchema = z.object({
  privkey: z.string(),
  cert: z.string(),
  chain: z.string(),
  fullchain: z.string(),
});

type LocalIp = z.infer<typeof localIpSchema>;

@Injectable()
export class LocalIpService implements OnApplicationBootstrap {
  private readonly logger = new Logger(LocalIpService.name);

  constructor(
    private readonly configService: ConfigService,
    private readonly schedulerRegistry: SchedulerRegistry,
    private readonly appSettingsService: AppSettingsService,
  ) {
    axiosRetry(axios, { retries: 2, retryDelay: exponentialDelay });
  }

  private httpsServer: https.Server | null = null;

  async onApplicationBootstrap() {
    const setting = await this.appSettingsService.get();
    const job = this.schedulerRegistry.getCronJob(LOCAL_IP_CRON_JOB);

    if (!setting.enebledlocalIp) {
      await job.stop();
      return;
    }

    await this.enable();
  }

  async enable() {
    if (this.httpsServer) return;

    const port = this.configService.getOrThrow<number>('app.https-port');

    const localIpKeys = await this.fetchKeys();

    this.httpsServer = https.createServer(
      {
        key: localIpKeys.privkey,
        cert: localIpKeys.fullchain,
      },
      EXPRESS,
    );

    this.httpsServer.listen(port, () => {
      this.logger.log(`✅ [local-ip] HTTPS elindult a ${port} porton`);
    });

    this.httpsServer.on('error', (error) => {
      this.logger.error('🛑 [local-ip] indítása sikertelen!', error);
      this.disable().catch(() => {});
    });

    const job = this.schedulerRegistry.getCronJob(LOCAL_IP_CRON_JOB);
    if (!job.isActive) job.start();
  }

  async disable() {
    const { httpsServer } = this;
    if (!httpsServer) return;

    await new Promise<void>((resolve, reject) =>
      httpsServer.close((err) => (err ? reject(err) : resolve())),
    );

    this.httpsServer = null;

    const job = this.schedulerRegistry.getCronJob(LOCAL_IP_CRON_JOB);
    if (job.isActive) await job.stop();
  }

  @Cron(CronExpression.EVERY_4_HOURS, { name: LOCAL_IP_CRON_JOB })
  async refreshKeys() {
    if (!this.httpsServer) return;

    try {
      const localIpKeys = await this.fetchKeys();
      this.httpsServer.setSecureContext({
        key: localIpKeys.privkey,
        cert: localIpKeys.fullchain,
      });
    } catch (error) {
      this.logger.error('🛑 [local-ip] kulcsok frissítése sikertelen!', error);
    }
  }

  private async fetchKeys(): Promise<LocalIp> {
    const { data } = await axios.get<unknown>(LOCAL_IP_KEYS_URL);

    const localIp = localIpSchema.parse(data);
    return localIp;
  }
}
