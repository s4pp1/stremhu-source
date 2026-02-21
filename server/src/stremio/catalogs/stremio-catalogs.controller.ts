import {
  BadRequestException,
  Controller,
  Get,
  Logger,
  NotFoundException,
  Param,
  ParseEnumPipe,
  UseGuards,
} from '@nestjs/common';
import { ApiOkResponse, ApiParam, ApiTags } from '@nestjs/swagger';

import { TokenGuard } from 'src/auth/guards/token.guard';
import { MediaTypeEnum } from 'src/common/enum/media-type.enum';

import { MetaDetailDto } from '../dto/meta-detail.dto';
import { MetaPreviewDto } from '../dto/meta-preview.dto';
import { MetaDto } from '../dto/meta.dto';
import { StremioCatalogDto } from '../dto/stremio-catalog.dto';
import { ParseExtraPipe } from '../pipe/parse-extra.pipe';
import { SEARCH_ID } from '../stremio.constants';
import type { ParsedExtra } from '../type/parsed-extra.type';
import { ParseCatalogIdPipe } from './pipe/parse-catalog-id.pipe';
import { StremioCatalogsService } from './stremio-catalogs.service';
import type { ParsedCatalogId } from './type/parsed-catalog-id.type';

@UseGuards(TokenGuard)
@Controller('/:token')
@ApiParam({
  name: 'token',
  required: true,
  type: 'string',
})
@ApiTags('Stremio / Catalogs')
export class StremioCatalogsController {
  private readonly logger = new Logger(StremioCatalogsController.name);

  constructor(private stremioCatalogService: StremioCatalogsService) {}

  @Get([
    '/catalog/:mediaType/:catalogId.json',
    '/catalog/:mediaType/:catalogId/:extra.json',
  ])
  @ApiParam({
    name: 'mediaType',
    required: true,
    enum: MediaTypeEnum,
    enumName: 'MediaTypeEnum',
  })
  @ApiOkResponse({ type: StremioCatalogDto })
  async catalog(
    @Param('mediaType', new ParseEnumPipe(MediaTypeEnum))
    mediaType: MediaTypeEnum,
    @Param('catalogId') catalogId: string,
    @Param('extra', ParseExtraPipe) extra: ParsedExtra,
  ): Promise<StremioCatalogDto> {
    const { search } = extra;
    if (
      mediaType !== MediaTypeEnum.MOVIE ||
      catalogId !== SEARCH_ID ||
      !search
    ) {
      return { metas: [] };
    }

    const [key, torrentId] = search.split('-');

    if (key !== 't') {
      return { metas: [] };
    }

    let metaPreviews: MetaPreviewDto[] = [];

    try {
      metaPreviews = await this.stremioCatalogService.getMetas(torrentId);
    } catch (error) {
      this.logger.error(`A lista lekérésénél hiba történt:`, error);
    }

    return { metas: metaPreviews };
  }

  @Get('/meta/:mediaType/:id.json')
  @ApiParam({
    name: 'mediaType',
    required: true,
    enum: MediaTypeEnum,
    enumName: 'MediaTypeEnum',
  })
  @ApiParam({
    name: 'id',
    required: true,
    type: 'string',
  })
  @ApiOkResponse({ type: MetaDetailDto })
  async meta(
    @Param('mediaType', new ParseEnumPipe(MediaTypeEnum))
    mediaType: MediaTypeEnum,
    @Param('id', ParseCatalogIdPipe) id: ParsedCatalogId,
  ): Promise<MetaDto> {
    const { tracker, torrentId, imdbId } = id;

    if (mediaType !== MediaTypeEnum.MOVIE) {
      throw new BadRequestException();
    }

    const meta = await this.stremioCatalogService.getMeta(
      tracker,
      torrentId,
      imdbId,
    );

    if (!meta) {
      throw new NotFoundException();
    }

    return { meta: meta };
  }
}
