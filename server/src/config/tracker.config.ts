import { registerAs } from '@nestjs/config';
import { z } from 'zod';

import { TrackerConfig } from './interfaces/tracker.interface';
import ZodUtil, { ZodConfig } from './utils/zod-util';

export default registerAs('tracker', () => {
  const configs: ZodConfig<TrackerConfig> = {
    'ncore-url': {
      value: process.env.NCORE_URL ?? 'https://ncore.pro',
      zod: z.string().trim().nonempty(),
    },
    'bithumen-url': {
      value: process.env.BITHUMEN_URL ?? 'https://bithumen.be',
      zod: z.string().trim().nonempty(),
    },
    'majomparade-url': {
      value: process.env.MAJOMPARADE_URL ?? 'https://majomparade.eu',
      zod: z.string().trim().nonempty(),
    },
  };

  return ZodUtil.validate<TrackerConfig>(configs);
});
