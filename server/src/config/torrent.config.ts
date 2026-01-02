import { registerAs } from '@nestjs/config';
import _ from 'lodash';
import { join } from 'node:path';
import { z } from 'zod';

import { TorrentClientEnum } from './enum/torrent-client.enum';
import { TorrentConfig } from './interfaces/torrent.interface';
import ZodUtil, { ZodConfig } from './utils/zod-util';

export default registerAs('torrent', () => {
  const port = process.env.TORRENT_PORT
    ? _.parseInt(process.env.TORRENT_PORT)
    : undefined;

  const peerLimit = process.env.TORRENT_PEER_LIMIT
    ? _.parseInt(process.env.TORRENT_PEER_LIMIT)
    : undefined;

  const storeCacheSlots = process.env.WEB_TORRENT_STORE_CACHE_SLOTS
    ? _.parseInt(process.env.WEB_TORRENT_STORE_CACHE_SLOTS)
    : undefined;

  const configs: ZodConfig<TorrentConfig> = {
    client: {
      value: process.env.TORRENT_CLIENT ?? TorrentClientEnum.WEB_TORRENT,
      zod: z.enum(TorrentClientEnum),
    },
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
      value: peerLimit ?? 20,
      zod: z.number().positive(),
    },
    'store-cache-slots': {
      value: storeCacheSlots ?? 10,
      zod: z.number().nonnegative(),
    },
  };

  return ZodUtil.validate<TorrentConfig>(configs);
});
