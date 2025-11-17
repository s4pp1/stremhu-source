import { Controller, Get, Res, UseGuards } from '@nestjs/common';
import {
  ApiParam,
  ApiPermanentRedirectResponse,
  ApiResponse,
  ApiTags,
} from '@nestjs/swagger';
import type { Response } from 'express';

import { StremioTokenGuard } from 'src/auth/guards/stremio-token.guard';

import { ManifestDto } from './dto/manifest.dto';
import { StremioService } from './stremio.service';

@UseGuards(StremioTokenGuard)
@Controller('/:token')
@ApiTags('Stremio')
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
    res.status(308).redirect('/');
  }

  @ApiResponse({ type: ManifestDto })
  @Get('/manifest.json')
  async manifest(): Promise<ManifestDto> {
    return this.stremioService.manifest();
  }
}
