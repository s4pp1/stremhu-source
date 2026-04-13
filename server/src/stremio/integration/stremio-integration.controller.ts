import {
  Controller,
  Get,
  Res,
  SerializeOptions,
  UseGuards,
} from '@nestjs/common';
import {
  ApiParam,
  ApiPermanentRedirectResponse,
  ApiTags,
} from '@nestjs/swagger';
import type { Response } from 'express';

import { TokenGuard } from 'src/auth/guards/token.guard';
import { StremioCoreService } from 'src/stremio/core/stremio-core.service';
import { ManifestDto } from 'src/stremio/dto/manifest.dto';

@UseGuards(TokenGuard)
@Controller('/:token/stremio')
@ApiTags('Stremio')
@ApiParam({
  name: 'token',
  required: true,
  type: 'string',
})
export class StremioIntegrationController {
  constructor(private readonly stremioService: StremioCoreService) {}

  @ApiPermanentRedirectResponse({ description: 'Átirányítás a UI felületre.' })
  @Get('/configure')
  configure(@Res() res: Response) {
    res.redirect(308, '/');
  }

  @SerializeOptions({ type: ManifestDto })
  @Get('/manifest.json')
  async manifest(): Promise<ManifestDto> {
    return this.stremioService.manifest();
  }
}
