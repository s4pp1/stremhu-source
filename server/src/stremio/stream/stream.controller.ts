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
import { ApiOkResponse, ApiParam, ApiTags } from '@nestjs/swagger';
import type { Request, Response } from 'express';
import * as mime from 'mime-types';
import { Readable, pipeline } from 'node:stream';
import rangeParser from 'range-parser';

import { StremioTokenGuard } from 'src/auth/guards/stremio-token.guard';
import { TrackerEnum } from 'src/trackers/enum/tracker.enum';

import { StreamMediaTypeEnum } from '../enums/stream-media-type.enum';
import { StreamsResponseDto } from './dto/stremio-stream.dto';
import { StreamIdPipe } from './pipe/stream-id.pipe';
import type { ParsedStreamId } from './pipe/stream-id.pipe';
import { StremioStreamService } from './stream.service';
import {
  CalculateRange,
  CalculatedRange,
  RangeErrorEnum,
} from './stream.types';

@UseGuards(StremioTokenGuard)
@Controller('/:token/stream')
@ApiTags('Stremio / Stream')
@ApiParam({
  name: 'token',
  required: true,
  description: 'Stremio addon token',
  schema: { type: 'string' },
})
export class StremioStreamController {
  private readonly logger = new Logger(StremioStreamController.name);

  constructor(private streamService: StremioStreamService) {}

  @ApiParam({
    name: 'id',
    schema: { type: 'string' },
    example: 'tt1234567:1:2',
  })
  @ApiParam({
    name: 'mediaType',
    enum: StreamMediaTypeEnum,
  })
  @ApiOkResponse({ type: StreamsResponseDto })
  @Get('/:mediaType/:id.json')
  async streams(
    @Req() req: Request,
    @Param('mediaType', new ParseEnumPipe(StreamMediaTypeEnum))
    mediaType: StreamMediaTypeEnum,
    @Param('id', StreamIdPipe) id: ParsedStreamId,
  ): Promise<StreamsResponseDto> {
    const { user } = req;

    const streams = await this.streamService.streams({
      user: user!,
      mediaType,
      ...id,
    });

    return {
      streams: streams,
    };
  }

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
    @Param('fileIdx', ParseIntPipe) fileIdx: number,
  ) {
    const rangeHeader = req.headers.range;

    const { torrent, file } = await this.streamService.playStream({
      imdbId,
      tracker,
      torrentId,
      fileIdx,
    });

    const contentType = mime.lookup(file.name) || 'application/octet-stream';

    const total = file.length;

    const calculatedRange = this.calculateRange({
      rangeHeader,
      torrentPieceLength: torrent.pieceLength,
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
        `❌ Stream hibára futott: ${err.message}, ${JSON.stringify(err)}`,
      );
    });
  }

  private calculateRange(payload: CalculateRange): CalculatedRange {
    const { rangeHeader, total } = payload;

    if (!rangeHeader) {
      return {
        start: 0,
        end: total - 1,
        contentLength: total,
      };
    }

    const parsedRange = rangeParser(total, rangeHeader);

    if (parsedRange === -1) return RangeErrorEnum.RANGE_NOT_SATISFIABLE;
    if (parsedRange === -2) return RangeErrorEnum.RANGE_MALFORMED;

    const [range] = parsedRange;

    return {
      start: range.start,
      end: range.end,
      contentLength: range.end - range.start + 1,
    };
  }
}
