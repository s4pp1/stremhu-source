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

import { StreamsResponseDto } from './dto/stremio-stream.dto';
import { ParseStreamIdPipe } from './pipe/parse-stream-id.pipe';
import { StreamsService } from './streams.service';
import type { ParsedStreamId } from './type/parsed-stream-id.type';

@UseGuards(TokenGuard)
@Controller('/:token/stream')
@ApiParam({
  name: 'token',
  required: true,
  type: 'string',
})
@ApiTags('Stremio / Streams')
export class StreamsController {
  constructor(private streamsService: StreamsService) {}

  @ApiParam({
    name: 'id',
    type: 'string',
  })
  @ApiParam({
    name: 'mediaType',
    enum: MediaTypeEnum,
  })
  @ApiOkResponse({ type: StreamsResponseDto })
  @Get('/:mediaType/:id.json')
  async streams(
    @Req() req: Request,
    @Param('mediaType', new ParseEnumPipe(MediaTypeEnum))
    mediaType: MediaTypeEnum,
    @Param('id', ParseStreamIdPipe) id: ParsedStreamId,
  ): Promise<StreamsResponseDto> {
    const { user } = req;

    const streams = await this.streamsService.streams(user!, mediaType, id);

    return {
      streams: streams,
    };
  }
}
