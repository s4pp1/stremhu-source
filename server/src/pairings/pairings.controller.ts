import {
  Body,
  Controller,
  HttpCode,
  Post,
  Req,
  UseGuards,
} from '@nestjs/common';
import { ApiTags } from '@nestjs/swagger';
import type { Request } from 'express';

import { AuthGuard } from 'src/auth/guards/auth.guard';

import { PairInitDto } from './dto/pair-init.dto';
import { PairStatusRequestDto } from './dto/pair-status-request.dto';
import { PairStatusDto } from './dto/pair-status.dto';
import { PairVerifyRequestDto } from './dto/pair-verify-request.dto';
import { PairVerifyDto } from './dto/pair-verify.dto';
import { PairingsService } from './pairings.service';

@Controller('auth/pair')
@ApiTags('Pairings')
export class PairingsController {
  constructor(private readonly pairingsService: PairingsService) {}

  @Post('/init')
  async init(): Promise<PairInitDto> {
    return this.pairingsService.generatePairingCodes();
  }

  @Post('/status')
  @HttpCode(200)
  async status(@Body() payload: PairStatusRequestDto): Promise<PairStatusDto> {
    return this.pairingsService.pollPairingStatus(payload.deviceCode);
  }

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
