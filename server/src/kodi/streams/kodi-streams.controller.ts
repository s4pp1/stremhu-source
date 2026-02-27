import { Controller, Get, Param, Query, Req, UseGuards } from '@nestjs/common';
import { ApiOkResponse, ApiParam, ApiTags } from '@nestjs/swagger';
import type { Request } from 'express';

import { TokenGuard } from 'src/auth/guards/token.guard';

import { FindKodiImdbStreamsDto } from './dto/find-kodi-imdb-streams.dto';
import { KodiImdbStreamDto } from './dto/kodi-imdb-stream.dto';
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

  @ApiOkResponse({ type: KodiImdbStreamsDto })
  @Get('/imdb/:imdbId/streams')
  async streams(
    @Req() req: Request,
    @Param('imdbId') imdbId: string,
    @Query() query?: FindKodiImdbStreamsDto,
  ): Promise<KodiImdbStreamsDto> {
    const { user } = req;

    const streams = await this.streamsService.imdbStreams(user!, imdbId, query);

    return {
      streams: streams.map(
        (stream): KodiImdbStreamDto => ({
          tracker: stream.tracker,
          torrentName: stream.torrentName,
          fileName: stream.fileName,
          seeders: stream.seeders,
          size: stream.fileSize,
          languages: [stream.language],
          resolution: stream.resolution,
          videoQualities: stream['video-quality'],
          audioQuality: stream['audio-quality'],
          audioSpatial: stream['audio-spatial'],
          source: stream.source,
          url: stream.playUrl,
        }),
      ),
      errors: [],
    };
  }
}
