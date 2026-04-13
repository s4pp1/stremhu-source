import {
  Controller,
  Get,
  Param,
  ParseEnumPipe,
  Req,
  SerializeOptions,
  UseGuards,
} from '@nestjs/common';
import { ApiParam, ApiTags } from '@nestjs/swagger';
import type { Request } from 'express';

import { TokenGuard } from 'src/auth/guards/token.guard';
import { MediaTypeEnum } from 'src/common/enum/media-type.enum';
import { StremioStreamsCoreService } from 'src/stremio/streams/core/stremio-streams-core.service';
import { StremioStreamsResponseDto } from 'src/stremio/streams/dto/stremio-stream.dto';
import { ParseStreamIdPipe } from 'src/stremio/streams/pipe/parse-stream-id.pipe';
import type { ParsedStreamId } from 'src/stremio/streams/type/parsed-stream-id.type';

@UseGuards(TokenGuard)
@Controller('/:token/stremio/stream')
@ApiParam({
  name: 'token',
  required: true,
  type: 'string',
})
@ApiTags('Stremio')
export class StremioStreamsIntegrationController {
  constructor(private stremioStreamsCoreService: StremioStreamsCoreService) {}

  @ApiParam({
    name: 'id',
    type: 'string',
  })
  @ApiParam({
    name: 'mediaType',
    enum: MediaTypeEnum,
  })
  @SerializeOptions({ type: StremioStreamsResponseDto })
  @Get('/:mediaType/:id.json')
  async streams(
    @Req() req: Request,
    @Param('mediaType', new ParseEnumPipe(MediaTypeEnum))
    mediaType: MediaTypeEnum,
    @Param('id', ParseStreamIdPipe) id: ParsedStreamId,
  ): Promise<StremioStreamsResponseDto> {
    const { user } = req;

    const streams = await this.stremioStreamsCoreService.streams(
      user!,
      mediaType,
      id,
    );

    return {
      streams: streams,
    };
  }
}
