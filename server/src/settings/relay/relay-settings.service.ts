import { Injectable } from '@nestjs/common';
import { isUndefined, omitBy } from 'lodash';
import { z } from 'zod';

import { SettingsStore } from '../core/settings.store';
import { TORRENT_SETTINGS } from '../settings.constant';

const RelaySettingsSchema = z.object({
  port: z.number().int().default(6881).catch(6881),
  downloadLimit: z.number().int().default(0).catch(0),
  uploadLimit: z.number().int().default(0).catch(0),
  connectionsLimit: z.number().int().default(200).catch(200),
  torrentConnectionsLimit: z.number().int().default(20).catch(20),
  enableUpnpAndNatpmp: z.boolean().default(false).catch(false),
});

export type RelaySettings = z.infer<typeof RelaySettingsSchema>;

@Injectable()
export class RelaySettingsService {
  constructor(private readonly settingsStore: SettingsStore) {}

  async get(): Promise<RelaySettings> {
    const settingRow = await this.settingsStore.findOneByKey(TORRENT_SETTINGS);
    const setting = settingRow?.value ?? {};
    return RelaySettingsSchema.parse(setting);
  }

  async update(payload: Partial<RelaySettings>): Promise<RelaySettings> {
    const current = await this.get();

    const update = omitBy(payload, isUndefined);
    const merged = RelaySettingsSchema.parse({ ...current, ...update });

    const entity = this.settingsStore.createEntity({
      key: TORRENT_SETTINGS,
      value: merged,
    });

    await this.settingsStore.createOrUpdate(entity);

    return merged;
  }
}
