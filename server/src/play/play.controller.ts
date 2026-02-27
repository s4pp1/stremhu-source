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

import { playProxy } from './play.proxy';
import { PlayService } from './play.service';

@UseGuards(TokenGuard)
@Controller('/:token/play')
@ApiParam({
  name: 'token',
  required: true,
  type: 'string',
})
@ApiTags('Play')
export class PlayController {
  private readonly logger = new Logger(PlayController.name);

  constructor(private playService: PlayService) {}

  @ApiParam({
    name: 'tracker',
    enum: TrackerEnum,
  })
  @Get('/:tracker/:torrentId/:fileIdx')
  async play(
    @Req() req: Request,
    @Res() res: Response,
    @Param('tracker', new ParseEnumPipe(TrackerEnum))
    tracker: TrackerEnum,
    @Param('torrentId') torrentId: string,
    @Param('fileIdx', ParseIntPipe) fileIndex: number,
  ) {
    const rangeHeader = req.headers.range;
    this.logger.log(
      `▶️ Lejátszás indítása "${req.method}"- "${rangeHeader}" range-el.`,
    );

    const relayTorrent = await this.playService.preparePlay({
      tracker,
      torrentId,
    });

    req.infoHash = relayTorrent.infoHash;
    req.fileIndex = fileIndex;

    return playProxy(req, res, (err) => {
      if (err) {
        this.logger.error(err);
        res.status(502).end();
      }
    });
  }
}
