import {
  Body,
  Controller,
  Get,
  Post,
  Req,
  SerializeOptions,
} from '@nestjs/common';
import { ApiTags } from '@nestjs/swagger';
import type { Request } from 'express';

import { UserDto } from 'src/users/dto/user.dto';

import { CreateSetupDto } from './dto/create-setup.dto';
import { StatusDto } from './dto/status.dto';
import { SetupService } from './setup.service';

@Controller('settings/setup')
@ApiTags('Settings')
export class SetupController {
  constructor(private readonly setupService: SetupService) {}

  @SerializeOptions({ type: UserDto })
  @Post('/')
  async create(
    @Req() req: Request,
    @Body() payload: CreateSetupDto,
  ): Promise<UserDto> {
    const user = await this.setupService.create(payload);
    req.session.userId = user.id;

    return user;
  }

  @SerializeOptions({ type: StatusDto })
  @Get('/status')
  async status(): Promise<StatusDto> {
    const status = await this.setupService.status();
    return status;
  }
}
