import { registerAs } from '@nestjs/config';
import _ from 'lodash';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { z } from 'zod';

import { NodeEnvEnum } from './enums/node-env.enum';
import { AppConfig } from './interfaces/app-config.interface';
import ZodUtil, { ZodConfig } from './utils/zod-util';

export default registerAs('app', () => {
  const packageSchema = z.object({
    version: z.string(),
    description: z.string(),
  });

  const packageJsonRaw = readFileSync(
    join(process.cwd(), 'package.json'),
    'utf8',
  );
  const parsed = packageSchema.safeParse(JSON.parse(packageJsonRaw));
  const version = parsed.success && parsed.data.version;
  const description = parsed.success && parsed.data.description;

  const httpPort = process.env.HTTP_PORT && _.parseInt(process.env.HTTP_PORT);
  const httpsPort =
    process.env.HTTPS_PORT && _.parseInt(process.env.HTTPS_PORT);

  const configs: ZodConfig<AppConfig> = {
    'node-env': {
      value: process.env.NODE_ENV ?? NodeEnvEnum.PRODUCTION,
      zod: z.enum(['dev', 'production']),
    },
    'client-path': {
      value: join(process.cwd(), '../client/dist'),
      zod: z.string(),
    },
    'http-port': {
      value: httpPort || 3000,
      zod: z.number(),
    },
    'https-port': {
      value: httpsPort || 3443,
      zod: z.number(),
    },
    'openapi-dir': {
      value: join(process.cwd(), '/openapi'),
      zod: z.string(),
    },
    version: {
      value: version,
      zod: z.string(),
    },
    description: {
      value: description,
      zod: z.string(),
    },
    'stremhu-catalog-url': {
      value: process.env.STREMHU_CATALOG_URL ?? 'https://catalog.stremhu.app',
      zod: z.string(),
    },
  };

  return ZodUtil.validate<AppConfig>(configs);
});
