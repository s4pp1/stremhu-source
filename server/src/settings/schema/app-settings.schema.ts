import { randomUUID } from 'node:crypto';
import { z } from 'zod';

import { DEFAULT_CACHE_RETENTION_SECONDS } from '../settings.constant';

export const AppSettingsSchema = z.object({
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
