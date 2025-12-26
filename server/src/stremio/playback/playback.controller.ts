import {
  Controller,
  Get,
  Logger,
  Param,
  ParseEnumPipe,
  ParseIntPipe,
  Req,
  Res,
  UseGuards,
} from '@nestjs/common';
import { ApiParam, ApiTags } from '@nestjs/swagger';
import type { Request, Response } from 'express';
import * as mime from 'mime-types';
import { Readable, pipeline } from 'node:stream';

import { TokenGuard } from 'src/auth/guards/token.guard';
import { TrackerEnum } from 'src/trackers/enum/tracker.enum';

import { RangeErrorEnum } from './enum/range-error.enum';
import { PlaybackService } from './playback.service';
import { calculateRange } from './util/calculate-range.util';

@UseGuards(TokenGuard)
@Controller('/:token/stream')
@ApiParam({
  name: 'token',
  required: true,
  type: 'string',
})
@ApiTags('Stremio / Playback')
export class PlaybackController {
  private readonly logger = new Logger(PlaybackController.name);

  constructor(private playbackService: PlaybackService) {}

  @ApiParam({
    name: 'tracker',
    enum: TrackerEnum,
  })
  @Get('/play/:imdbId/:tracker/:torrentId/:fileIdx')
  async playStream(
    @Req() req: Request,
    @Res() res: Response,
    @Param('imdbId') imdbId: string,
    @Param('tracker', new ParseEnumPipe(TrackerEnum))
    tracker: TrackerEnum,
    @Param('torrentId') torrentId: string,
    @Param('fileIdx', ParseIntPipe) fileIndex: number,
  ) {
    const rangeHeader = req.headers.range;

    const file = await this.playbackService.play({
      imdbId,
      tracker,
      torrentId,
      fileIndex,
    });

    const contentType = mime.lookup(file.name) || 'application/octet-stream';

    const total = file.length;

    const calculatedRange = calculateRange({
      rangeHeader,
      total,
    });

    if (
      calculatedRange === RangeErrorEnum.RANGE_MALFORMED ||
      calculatedRange === RangeErrorEnum.RANGE_NOT_SATISFIABLE
    ) {
      res.status(416);
      res.setHeader('Content-Range', `bytes */${total}`);
      return res.end();
    }

    res.setHeader('Content-Type', contentType);
    res.setHeader('Accept-Ranges', 'bytes');

    const { start, end, contentLength } = calculatedRange;

    if (rangeHeader === undefined) {
      res.status(200);
      res.setHeader('Content-Length', `${total}`);
    } else {
      res.status(206);
      res.setHeader('Content-Length', `${contentLength}`);
      res.setHeader('Cache-Control', 'no-store, no-transform');
      res.setHeader('Content-Range', `bytes ${start}-${end}/${total}`);
    }

    if (req.method === 'HEAD') {
      return res.end();
    }

    const stream = file.createReadStream({ start, end }) as Readable;

    pipeline(stream, res, (err) => {
      if (!err) return;

      if (err.code === 'ERR_STREAM_PREMATURE_CLOSE') {
        if (!stream.destroyed) stream.destroy();
        return;
      }

      this.logger.error(
        `🚨 Stream hibára futott: ${err.message}, ${JSON.stringify(err)}`,
      );
    });
  }
}
