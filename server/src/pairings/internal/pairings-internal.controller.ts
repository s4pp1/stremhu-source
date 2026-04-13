import {
  Body,
  Controller,
  HttpCode,
  Post,
  Req,
  SerializeOptions,
  UseGuards,
} from '@nestjs/common';
import { ApiTags } from '@nestjs/swagger';
import type { Request } from 'express';

import { AuthGuard } from 'src/auth/guards/auth.guard';

import { PairingsCoreService } from '../core/pairings-core.service';
import { PairVerifyRequestDto } from '../dto/pair-verify-request.dto';
import { PairVerifyDto } from '../dto/pair-verify.dto';

@Controller('auth/pair')
@ApiTags('Pairings')
export class PairingsInternalController {
  constructor(private readonly pairingsService: PairingsCoreService) {}

  @SerializeOptions({ type: PairVerifyDto })
  @UseGuards(AuthGuard)
  @Post('/verify')
  @HttpCode(200)
  async verify(
    @Req() req: Request,
    @Body() payload: PairVerifyRequestDto,
  ): Promise<PairVerifyDto> {
    return this.pairingsService.authorizePairingCode(
      payload.userCode,
      req.user!,
    );
  }
}
