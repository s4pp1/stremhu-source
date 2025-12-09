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
    version: z.string().trim().nonempty().optional(),
    description: z.string().trim().nonempty(),
  });

  const packageJsonRaw = readFileSync(
    join(process.cwd(), 'package.json'),
    'utf8',
  );
  const parsed = packageSchema.safeParse(JSON.parse(packageJsonRaw));

  if (!parsed.success) {
    throw new Error('package.json parse hiba');
  }

  const version = parsed.data.version ?? '0.0.0';
  const description = parsed.data.description;

  const httpPort = process.env.HTTP_PORT
    ? _.parseInt(process.env.HTTP_PORT)
    : undefined;
  const httpsPort = process.env.HTTPS_PORT
    ? _.parseInt(process.env.HTTPS_PORT)
    : undefined;

  const configs: ZodConfig<AppConfig> = {
    'node-env': {
      value: process.env.NODE_ENV ?? NodeEnvEnum.PRODUCTION,
      zod: z.enum(['dev', 'production']),
    },
    'client-path': {
      value: join(process.cwd(), '../client/dist'),
      zod: z.string().trim().nonempty(),
    },
    'http-port': {
      value: httpPort || 3000,
      zod: z.number().positive(),
    },
    'https-port': {
      value: httpsPort || 3443,
      zod: z.number().positive(),
    },
    'openapi-dir': {
      value: join(process.cwd(), '/openapi'),
      zod: z.string().trim().nonempty(),
    },
    version: {
      value: version,
      zod: z.string().trim().nonempty(),
    },
    description: {
      value: description,
      zod: z.string().trim().nonempty(),
    },
    'stremhu-catalog-url': {
      value: process.env.STREMHU_CATALOG_URL ?? 'https://catalog.stremhu.app',
      zod: z.string().trim().nonempty(),
    },
  };

  return ZodUtil.validate<AppConfig>(configs);
});
