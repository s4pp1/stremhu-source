import {
  BadRequestException,
  Controller,
  Get,
  Logger,
  NotFoundException,
  Param,
  ParseEnumPipe,
  SerializeOptions,
  UseGuards,
} from '@nestjs/common';
import { ApiParam, ApiTags } from '@nestjs/swagger';

import { TokenGuard } from 'src/auth/guards/token.guard';
import { MediaTypeEnum } from 'src/common/enum/media-type.enum';
import { StremioCatalogsCoreService } from 'src/stremio/catalogs/core/stremio-catalogs-core.service';
import { ParseCatalogIdPipe } from 'src/stremio/catalogs/pipe/parse-catalog-id.pipe';
import type { ParsedCatalogId } from 'src/stremio/catalogs/type/parsed-catalog-id.type';
import { MetaPreviewDto } from 'src/stremio/dto/meta-preview.dto';
import { MetaDto } from 'src/stremio/dto/meta.dto';
import { StremioCatalogDto } from 'src/stremio/dto/stremio-catalog.dto';
import { ParseExtraPipe } from 'src/stremio/pipe/parse-extra.pipe';
import { SEARCH_ID } from 'src/stremio/stremio.constants';
import type { ParsedExtra } from 'src/stremio/type/parsed-extra.type';

@UseGuards(TokenGuard)
@Controller('/:token/stremio')
@ApiParam({
  name: 'token',
  required: true,
  type: 'string',
})
@ApiTags('Stremio')
export class StremioCatalogsIntegrationController {
  private readonly logger = new Logger(
    StremioCatalogsIntegrationController.name,
  );

  constructor(private stremioCatalogsCoreService: StremioCatalogsCoreService) {}

  @SerializeOptions({ type: StremioCatalogDto })
  @Get('/catalog/:mediaType/:catalogId.json')
  @ApiParam({
    name: 'mediaType',
    required: true,
    enum: MediaTypeEnum,
    enumName: 'MediaTypeEnum',
  })
  async catalog(
    @Param('mediaType', new ParseEnumPipe(MediaTypeEnum))
    mediaType: MediaTypeEnum,
    @Param('catalogId') catalogId: string,
  ): Promise<StremioCatalogDto> {
    return this.getCatalog(mediaType, catalogId);
  }

  @SerializeOptions({ type: StremioCatalogDto })
  @Get('/catalog/:mediaType/:catalogId/:extra.json')
  @ApiParam({
    name: 'mediaType',
    required: true,
    enum: MediaTypeEnum,
    enumName: 'MediaTypeEnum',
  })
  @ApiParam({
    name: 'extra',
    required: true,
    type: 'string',
    description:
      'Kiegészítő szűrési paraméterek az útvonalban, például keresési kifejezés, eltolás (lapozás) vagy műfaj (pl. "search=film+neve&skip=20").',
  })
  async catalogWithExtra(
    @Param('mediaType', new ParseEnumPipe(MediaTypeEnum))
    mediaType: MediaTypeEnum,
    @Param('catalogId') catalogId: string,
    @Param('extra', ParseExtraPipe) extra: ParsedExtra,
  ): Promise<StremioCatalogDto> {
    return this.getCatalog(mediaType, catalogId, extra);
  }

  private async getCatalog(
    mediaType: MediaTypeEnum,
    catalogId: string,
    extra: ParsedExtra = {},
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
      metaPreviews = await this.stremioCatalogsCoreService.getMetas(torrentId);
    } catch (error) {
      this.logger.error(`A lista lekérésénél hiba történt:`, error);
    }

    return { metas: metaPreviews };
  }

  @SerializeOptions({ type: MetaDto })
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
  async meta(
    @Param('mediaType', new ParseEnumPipe(MediaTypeEnum))
    mediaType: MediaTypeEnum,
    @Param('id', ParseCatalogIdPipe) id: ParsedCatalogId,
  ): Promise<MetaDto> {
    const { tracker, torrentId } = id;

    if (mediaType !== MediaTypeEnum.MOVIE) {
      throw new BadRequestException();
    }

    const meta = await this.stremioCatalogsCoreService.getMeta(
      tracker,
      torrentId,
    );

    if (!meta) {
      throw new NotFoundException();
    }

    return { meta: meta };
  }
}
