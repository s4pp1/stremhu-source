import {
  Controller,
  Get,
  Param,
  ParseEnumPipe,
  Req,
  UseGuards,
} from '@nestjs/common';
import { ApiOkResponse, ApiParam, ApiTags } from '@nestjs/swagger';
import type { Request } from 'express';

import { TokenGuard } from 'src/auth/guards/token.guard';
import { MediaTypeEnum } from 'src/common/enum/media-type.enum';

import { StremioStreamsResponseDto } from './dto/stremio-stream.dto';
import { ParseStreamIdPipe } from './pipe/parse-stream-id.pipe';
import { StremioStreamsService } from './stremio-streams.service';
import type { ParsedStreamId } from './type/parsed-stream-id.type';

@UseGuards(TokenGuard)
@Controller('/:token/stremio/stream')
@ApiParam({
  name: 'token',
  required: true,
  type: 'string',
})
@ApiTags('Stremio / Streams')
export class StremioStreamsController {
  constructor(private streamsService: StremioStreamsService) {}

  @ApiParam({
    name: 'id',
    type: 'string',
  })
  @ApiParam({
    name: 'mediaType',
    enum: MediaTypeEnum,
  })
  @ApiOkResponse({ type: StremioStreamsResponseDto })
  @Get('/:mediaType/:id.json')
  async streams(
    @Req() req: Request,
    @Param('mediaType', new ParseEnumPipe(MediaTypeEnum))
    mediaType: MediaTypeEnum,
    @Param('id', ParseStreamIdPipe) id: ParsedStreamId,
  ): Promise<StremioStreamsResponseDto> {
    const { user } = req;

    const streams = await this.streamsService.streams(user!, mediaType, id);

    return {
      streams: streams,
    };
  }
}
