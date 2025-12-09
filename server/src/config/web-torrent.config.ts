import { registerAs } from '@nestjs/config';
import _ from 'lodash';
import { join } from 'node:path';
import { z } from 'zod';

import { WebTorrentConfig } from './interfaces/web-torrent.interface';
import ZodUtil, { ZodConfig } from './utils/zod-util';

export default registerAs('web-torrent', () => {
  const port = process.env.WEB_TORRENT_PORT
    ? _.parseInt(process.env.WEB_TORRENT_PORT)
    : undefined;

  const peerLimit = process.env.WEB_TORRENT_PEER_LIMIT
    ? _.parseInt(process.env.WEB_TORRENT_PEER_LIMIT)
    : undefined;

  const storeCacheSlots = process.env.WEB_TORRENT_STORE_CACHE_SLOTS
    ? _.parseInt(process.env.WEB_TORRENT_STORE_CACHE_SLOTS)
    : undefined;

  const configs: ZodConfig<WebTorrentConfig> = {
    port: {
      value: port || 6881,
      zod: z.number().positive(),
    },
    'downloads-dir': {
      value: join(process.cwd(), '../data/downloads'),
      zod: z.string().trim().nonempty(),
    },
    'torrents-dir': {
      value: join(process.cwd(), '../data/torrents'),
      zod: z.string().trim().nonempty(),
    },
    'peer-limit': {
      value: peerLimit ?? 10,
      zod: z.number().positive(),
    },
    'store-cache-slots': {
      value: storeCacheSlots ?? 10,
      zod: z.number().nonnegative(),
    },
  };

  return ZodUtil.validate<WebTorrentConfig>(configs);
});
