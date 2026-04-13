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
import { PlayCoreService } from 'src/play/core/play-core.service';
import { playIntegrationProxy } from 'src/play/integration/play-integration.proxy';
import { TrackerEnum } from 'src/trackers/enum/tracker.enum';

@UseGuards(TokenGuard)
@Controller('/:token/play')
@ApiParam({
  name: 'token',
  required: true,
  type: 'string',
})
@ApiTags('Lejátszás')
export class PlayIntegrationController {
  private readonly logger = new Logger(PlayIntegrationController.name);

  constructor(private playCoreService: PlayCoreService) {}

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

    const relayTorrent = await this.playCoreService.preparePlay({
      tracker,
      torrentId,
    });

    req.infoHash = relayTorrent.infoHash;
    req.fileIndex = fileIndex;

    return playIntegrationProxy(req, res, (err) => {
      if (err) {
        this.logger.error(err);
        res.status(502).end();
      }
    });
  }
}
