import { Inject, Injectable, Logger } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { createReadStream as fsCreateReadStream } from 'node:fs';
import path from 'node:path';
import { Readable } from 'node:stream';
import { setTimeout } from 'node:timers/promises';

import { LibTorrentClient } from './client';
import { LIBTORRENT_CLIENT } from './libtorrent-client.token';
import { CreateReadStream } from './type/create-read-stream.type';

const MIN_WINDOW_PIECES = 8;

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
      'web-torrent.downloads-dir',
    );
  }

  createReadStream(payload: CreateReadStream): Readable {
    try {
      const streamIterator = this.streamIterator(payload);
      return Readable.from(streamIterator);
    } catch (error) {
      console.log('Leállt a lejátszás', error);
      throw error;
    }
  }

  async *streamIterator(payload: CreateReadStream) {
    const { infoHash, fileIndex, start, end } = payload;

    if (start > end) {
      throw new Error(`A "start" nem lehet nagyobb, mint az "end".`);
    }

    const file = await this.libtorrentClient.torrents.getTorrentFile(
      infoHash,
      fileIndex,
    );

    if (start >= file.size) {
      throw new Error(
        `A "start" nem lehet nagyobb vagy egyenlő, mint a "file.size".`,
      );
    }

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
        const windowBytes = MIN_WINDOW_PIECES * file.piece_length;
        const endByte = Math.min(currentByte + windowBytes - 1, safeEnd);

        await this.libtorrentClient.torrents.prioritizePiecesRange(
          infoHash,
          fileIndex,
          {
            start_byte: currentByte,
            end_byte: endByte,
          },
        );

        const checkedRange =
          await this.libtorrentClient.torrents.checkPiecesRangeAvailable(
            infoHash,
            fileIndex,
            {
              start_byte: currentByte,
              end_byte: endByte,
            },
          );

        if (!checkedRange.ready) {
          await setTimeout(200);
          continue;
        }

        let streamEndByte = endByte;

        if (checkedRange.is_available) {
          streamEndByte = safeEnd;
        }

        const chunks = fsCreateReadStream(torrentFilePath, {
          start: currentByte,
          end: streamEndByte,
        });
        for await (const chunk of chunks) {
          yield chunk;
        }

        currentByte = streamEndByte + 1;
      }
    } finally {
      streamClosed = true;
      await this.libtorrentClient.torrents.resetPiecesPriorities(
        infoHash,
        fileIndex,
      );
    }
  }
}
