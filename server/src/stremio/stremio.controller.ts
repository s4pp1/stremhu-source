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

import { ManifestDto } from './dto/manifest.dto';
import { StremioService } from './stremio.service';

@UseGuards(TokenGuard)
@Controller('/:token/stremio')
@ApiTags('Stremio / Manifest')
@ApiParam({
  name: 'token',
  required: true,
  type: 'string',
})
export class StremioController {
  constructor(private readonly stremioService: StremioService) {}

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
