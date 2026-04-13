import {
  Body,
  Controller,
  HttpCode,
  Post,
  SerializeOptions,
} from '@nestjs/common';
import { ApiTags } from '@nestjs/swagger';

import { PairingsCoreService } from '../core/pairings-core.service';
import { PairInitDto } from '../dto/pair-init.dto';
import { PairStatusRequestDto } from '../dto/pair-status-request.dto';
import { PairStatusDto } from '../dto/pair-status.dto';

@Controller('auth/pair')
@ApiTags('Pairings')
export class PairingsIntegrationController {
  constructor(private readonly pairingsService: PairingsCoreService) {}

  @SerializeOptions({ type: PairInitDto })
  @Post('/init')
  async init(): Promise<PairInitDto> {
    return this.pairingsService.generatePairingCodes();
  }

  @SerializeOptions({ type: PairStatusDto })
  @Post('/status')
  @HttpCode(200)
  async status(@Body() payload: PairStatusRequestDto): Promise<PairStatusDto> {
    return this.pairingsService.pollPairingStatus(payload.deviceCode);
  }
}
