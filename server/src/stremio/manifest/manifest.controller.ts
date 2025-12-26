import { Controller, Get, Res, UseGuards } from '@nestjs/common';
import {
  ApiParam,
  ApiPermanentRedirectResponse,
  ApiResponse,
  ApiTags,
} from '@nestjs/swagger';
import type { Response } from 'express';

import { TokenGuard } from 'src/auth/guards/token.guard';

import { ManifestDto } from '../dto/manifest.dto';
import { ManifestService } from './manifest.service';

@UseGuards(TokenGuard)
@Controller('/:token')
@ApiTags('Stremio / Manifest')
@ApiParam({
  name: 'token',
  required: true,
  type: 'string',
})
export class ManifestController {
  constructor(private readonly manifestService: ManifestService) {}

  @ApiPermanentRedirectResponse({ description: 'Átirányítás a UI felületre.' })
  @Get('/configure')
  configure(@Res() res: Response) {
    res.status(308).redirect('/');
  }

  @ApiResponse({ type: ManifestDto })
  @Get('/manifest.json')
  async manifest(): Promise<ManifestDto> {
    return this.manifestService.manifest();
  }
}
