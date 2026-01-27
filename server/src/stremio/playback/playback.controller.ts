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

import { TokenGuard } from 'src/auth/guards/token.guard';
import { TrackerEnum } from 'src/trackers/enum/tracker.enum';

import { streamProxyMiddleware } from './playback.proxy';
import { PlaybackService } from './playback.service';

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
    this.logger.log(
      `▶️ Lejátszás indítása "${req.method}"- "${rangeHeader}" range-el.`,
    );

    const relayTorrent = await this.playbackService.preparePlayback({
      imdbId,
      tracker,
      torrentId,
    });

    req.infoHash = relayTorrent.infoHash;
    req.fileIndex = fileIndex;

    return streamProxyMiddleware(req, res, (err) => {
      if (err) {
        this.logger.error(err);
        res.status(502).end();
      }
    });
  }
}
