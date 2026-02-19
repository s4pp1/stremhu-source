import { registerAs } from '@nestjs/config';
import { parseInt } from 'lodash';
import { join } from 'node:path';
import { z } from 'zod';

import { TorrentClientEnum } from './enum/torrent-client.enum';
import { TorrentConfig } from './interfaces/torrent.interface';
import ZodUtil, { ZodConfig } from './utils/zod-util';

export default registerAs('torrent', () => {
  const port = process.env.TORRENT_PORT
    ? parseInt(process.env.TORRENT_PORT)
    : undefined;

  const configs: ZodConfig<TorrentConfig> = {
    client: {
      value: process.env.TORRENT_CLIENT ?? TorrentClientEnum.LIBTORRENT,
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
  };

  return ZodUtil.validate<TorrentConfig>(configs);
});
