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
import { KodiStreamsCoreService } from 'src/kodi/streams/core/kodi-streams-core.service';
import { FindKodiImdbStreamsDto } from 'src/kodi/streams/dto/find-kodi-imdb-streams.dto';
import { KodiImdbStreamsDto } from 'src/kodi/streams/dto/kodi-imdb-streams.dto';

@UseGuards(TokenGuard)
@Controller('/:token/kodi')
@ApiParam({
  name: 'token',
  required: true,
  type: 'string',
})
@ApiTags('Kodi')
export class KodiIntegrationController {
  constructor(
    private readonly kodiStreamsCoreService: KodiStreamsCoreService,
  ) {}

  @SerializeOptions({ type: KodiImdbStreamsDto })
  @Get('/imdb/:imdbId/streams')
  async streams(
    @Req() req: Request,
    @Param('imdbId') imdbId: string,
    @Query() query?: FindKodiImdbStreamsDto,
  ): Promise<KodiImdbStreamsDto> {
    const { user } = req;

    const streams = await this.kodiStreamsCoreService.imdbStreams(
      user!,
      imdbId,
      query,
    );

    return streams;
  }
}
