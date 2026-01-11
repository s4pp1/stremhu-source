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
import { StreamIterator } from './type/stream-iterator.type';

const WAIT_TIMEOUT_MS = 40_000;

@Injectable()
export class LibtorrentStreamService {
  private readonly logger = new Logger(LibtorrentStreamService.name);

  private readonly downloadsDir: string;

  private fileStreams = new Set<string>();

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
    const stremId = randomUUID();

    const streamIterator = this.streamIterator({ ...payload, stremId });
    const fileStream = Readable.from(streamIterator);

    this.fileStreams.add(stremId);

    fileStream.once('end', () => this.cleanup({ ...payload, stremId }));
    fileStream.once('close', () => this.cleanup({ ...payload, stremId }));
    fileStream.once('error', () => this.cleanup({ ...payload, stremId }));

    return fileStream;
  }

  async *streamIterator(payload: StreamIterator) {
    const { infoHash, fileIndex, start, end, file, stremId } = payload;

    const fileEnd = file.size - 1;
    const safeEnd = Math.min(end, fileEnd);

    const torrentFilePath = path.join(this.downloadsDir, file.path);

    if (file.is_available) {
      const chunks = fsCreateReadStream(torrentFilePath, {
        start: start,
        end: safeEnd,
      });

      for await (const chunk of chunks) {
        if (!this.fileStreams.has(stremId)) {
          chunks.destroy();
          return;
        }

        yield chunk;
      }
    } else {
      let currentByte = start;

      while (currentByte <= safeEnd) {
        if (!this.fileStreams.has(stremId)) return;

        const deadline = Date.now() + WAIT_TIMEOUT_MS;

        let endByte: number | null = null;

        do {
          if (!this.fileStreams.has(stremId)) return;

          const { end_byte } =
            await this.libtorrentClient.torrents.prioritizeAndWait(
              infoHash,
              fileIndex,
              stremId,
              { start_byte: currentByte, end_byte: safeEnd },
            );

          endByte = end_byte;

          if (Date.now() >= deadline) {
            this.logger.error(
              `🛑 ${WAIT_TIMEOUT_MS / 1000} másodperc alatt nem sikerül letölteni a következő darabot.`,
            );
            return;
          }

          if (endByte === null) {
            await setTimeout(250);
          }
        } while (endByte === null);

        const chunks = fsCreateReadStream(torrentFilePath, {
          start: currentByte,
          end: endByte,
        });

        for await (const chunk of chunks) {
          if (!this.fileStreams.has(stremId)) {
            chunks.destroy();
            return;
          }

          yield chunk;
        }

        currentByte = endByte + 1;
      }
    }
  }

  private cleanup(payload: StreamIterator) {
    const { infoHash, fileIndex, stremId } = payload;

    if (!this.fileStreams.delete(stremId)) return;

    this.libtorrentClient.torrents.resetPiecesPriorities(
      infoHash,
      fileIndex,
      stremId,
    );
  }
}
