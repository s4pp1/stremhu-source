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

import { StreamMediaTypeEnum } from '../enum/stream-media-type.enum';
import { StreamsResponseDto } from './dto/stremio-stream.dto';
import { StreamIdPipe } from './pipe/stream-id.pipe';
import type { ParsedStreamId } from './pipe/stream-id.pipe';
import { StreamsService } from './streams.service';

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

    const streams = await this.streamsService.streams({
      user: user!,
      mediaType,
      ...id,
    });

    return {
      streams: streams,
    };
  }
}
