import { registerAs } from '@nestjs/config';
import { parseInt } from 'lodash';
import { z } from 'zod';

import { TrackerConfig } from './interfaces/tracker.interface';
import ZodUtil, { ZodConfig } from './utils/zod-util';

export default registerAs('tracker', () => {
  function getMaxConcurrent(envName: string) {
    return process.env[envName] ? parseInt(process.env[envName]) : undefined;
  }

  const configs: ZodConfig<TrackerConfig> = {
    'ncore-url': {
      value: process.env.NCORE_URL ?? 'https://ncore.pro',
      zod: z.string().trim().nonempty(),
    },
    'ncore-max-concurrent': {
      value: getMaxConcurrent('NCORE_MAX_CONCURRENT') || 5,
      zod: z.number().positive(),
    },

    'bithumen-url': {
      value: process.env.BITHUMEN_URL ?? 'https://bithumen.be',
      zod: z.string().trim().nonempty(),
    },
    'bithumen-max-concurrent': {
      value: getMaxConcurrent('BITHUMEN_MAX_CONCURRENT') || 5,
      zod: z.number().positive(),
    },

    'insane-url': {
      value: process.env.INSANE_URL ?? 'https://newinsane.info',
      zod: z.string().trim().nonempty(),
    },
    'insane-max-concurrent': {
      value: getMaxConcurrent('INSANE_MAX_CONCURRENT') || 5,
      zod: z.number().positive(),
    },

    'majomparade-url': {
      value: process.env.MAJOMPARADE_URL ?? 'https://majomparade.eu',
      zod: z.string().trim().nonempty(),
    },
    'majomparade-max-concurrent': {
      value: getMaxConcurrent('MAJOMPARADE_MAX_CONCURRENT') || 5,
      zod: z.number().positive(),
    },
  };

  return ZodUtil.validate<TrackerConfig>(configs);
});
