import {
  Controller,
  Get,
  Param,
  Query,
  Req,
  SerializeOptions,
  UseGuards,
} from '@nestjs/common';
import { ApiParam, ApiTags } from '@nestjs/swagger';
import type { Request } from 'express';

import { TokenGuard } from 'src/auth/guards/token.guard';

import { FindKodiImdbStreamsDto } from './dto/find-kodi-imdb-streams.dto';
import { KodiImdbStreamsDto } from './dto/kodi-imdb-streams.dto';
import { KodiStreamsService } from './kodi-streams.service';

@UseGuards(TokenGuard)
@Controller('/:token/kodi')
@ApiParam({
  name: 'token',
  required: true,
  type: 'string',
})
@ApiTags('Kodi / Streams')
export class KodiStreamsController {
  constructor(private readonly streamsService: KodiStreamsService) {}

  @SerializeOptions({ type: KodiImdbStreamsDto })
  @Get('/imdb/:imdbId/streams')
  async streams(
    @Req() req: Request,
    @Param('imdbId') imdbId: string,
    @Query() query?: FindKodiImdbStreamsDto,
  ): Promise<KodiImdbStreamsDto> {
    const { user } = req;

    const streams = await this.streamsService.imdbStreams(user!, imdbId, query);

    return streams;
  }
}
