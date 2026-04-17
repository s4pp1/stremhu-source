import { registerAs } from '@nestjs/config';
import { join } from 'node:path';
import { z } from 'zod';

import { DatabaseConfig } from './interfaces/database-config.interface';
import ZodUtil, { ZodConfig } from './utils/zod-util';

export default registerAs('database', () => {
  const configs: ZodConfig<DatabaseConfig> = {
    'db-path': {
      value: join(process.cwd(), '../data/system/database/app.db'),
      zod: z.string().trim().nonempty(),
    },
  };

  return ZodUtil.validate<DatabaseConfig>(configs);
});
