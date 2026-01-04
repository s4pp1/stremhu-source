import { Inject, Injectable, Logger } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { randomUUID } from 'node:crypto';
import { createReadStream as fsCreateReadStream } from 'node:fs';
import path from 'node:path';
import { Readable } from 'node:stream';
import { setTimeout } from 'node:timers/promises';

import { LibTorrentClient } from './client';
import { LIBTORRENT_CLIENT } from './libtorrent-client.token';
import { CreateReadStream } from './type/create-read-stream.type';

@Injectable()
export class LibtorrentStreamService {
  private readonly logger = new Logger(LibtorrentStreamService.name);

  private readonly downloadsDir: string;

  constructor(
    @Inject(LIBTORRENT_CLIENT)
    private readonly libtorrentClient: LibTorrentClient,
    private readonly configService: ConfigService,
  ) {
    this.downloadsDir = this.configService.getOrThrow<string>(
      'torrent.downloads-dir',
    );
  }

  createReadStream(payload: CreateReadStream): Readable {
    const streamIterator = this.streamIterator(payload);
    return Readable.from(streamIterator);
  }

  async *streamIterator(payload: CreateReadStream) {
    const { infoHash, fileIndex, start, end, file } = payload;
    const stremId = randomUUID();

    const fileEnd = file.size - 1;
    const safeEnd = Math.min(end, fileEnd);

    const torrentFilePath = path.join(this.downloadsDir, file.path);

    if (file.is_available) {
      const chunks = fsCreateReadStream(torrentFilePath, {
        start: start,
        end: safeEnd,
      });

      for await (const chunk of chunks) {
        yield chunk;
      }

      return;
    }

    let streamClosed = false;

    try {
      let currentByte = start;

      while (currentByte <= safeEnd && !streamClosed) {
        let endByte: number | null = null;

        do {
          const { end_byte } =
            await this.libtorrentClient.torrents.prioritizeAndWait(
              infoHash,
              fileIndex,
              stremId,
              { start_byte: currentByte },
            );

          endByte = end_byte;

          if (endByte === null) {
            this.logger.log(`A(z) "${currentByte}" még nem érhető el.`);
            await setTimeout(250);
          }
        } while (endByte === null);

        const chunks = fsCreateReadStream(torrentFilePath, {
          start: currentByte,
          end: endByte,
        });

        for await (const chunk of chunks) {
          yield chunk;
        }

        currentByte = endByte + 1;
      }
    } finally {
      streamClosed = true;
      await this.libtorrentClient.torrents.resetPiecesPriorities(
        infoHash,
        fileIndex,
        stremId,
      );
    }
  }
}
