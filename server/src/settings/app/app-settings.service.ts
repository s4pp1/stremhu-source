import { Injectable } from '@nestjs/common';
import { isUndefined, omitBy } from 'lodash';
import { randomUUID } from 'node:crypto';
import { z } from 'zod';

import { SettingsStore } from '../core/settings.store';
import {
  APP_SETTINGS,
  DEFAULT_CACHE_RETENTION_SECONDS,
} from '../settings.constant';

const AppSettingsSchema = z.object({
  instanceId: z.string().default(randomUUID()),
  enebledlocalIp: z.boolean().default(true).catch(true),
  address: z.string().nullable().default(null).catch(null),
  hitAndRun: z.boolean().default(true).catch(true),
  keepSeedSeconds: z.number().int().default(0).catch(0),
  cacheRetentionSeconds: z
    .number()
    .int()
    .default(DEFAULT_CACHE_RETENTION_SECONDS)
    .catch(DEFAULT_CACHE_RETENTION_SECONDS),
  catalogToken: z.string().nullable().default(null).catch(null),
});

export type AppSettings = z.infer<typeof AppSettingsSchema>;

@Injectable()
export class AppSettingsService {
  constructor(private readonly settingsStore: SettingsStore) {}

  async get(): Promise<AppSettings> {
    const settingRow = await this.settingsStore.findOneByKey(APP_SETTINGS);
    const setting = settingRow?.value ?? {};
    return AppSettingsSchema.parse(setting);
  }

  async update(payload: Partial<AppSettings>): Promise<AppSettings> {
    const current = await this.get();

    const update = omitBy(payload, isUndefined);
    const merged = AppSettingsSchema.parse({ ...current, ...update });

    const entity = this.settingsStore.createEntity({
      key: APP_SETTINGS,
      value: merged,
    });

    await this.settingsStore.createOrUpdate(entity);

    return merged;
  }
}
