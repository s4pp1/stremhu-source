import { Body, Controller, Get, Post, Req } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { ApiOkResponse, ApiResponse, ApiTags } from '@nestjs/swagger';
import type { Request } from 'express';

import { toDto } from 'src/common/utils/to-dto';
import { UserDto } from 'src/users/dto/user.dto';

import { CreateSetupDto } from './dto/create-setup.dto';
import { StatusDto } from './dto/status.dto';
import { SetupService } from './setup.service';

@Controller('settings/setup')
@ApiTags('Settings')
export class SetupController {
  constructor(
    private configService: ConfigService,
    private setupService: SetupService,
  ) {}

  @ApiResponse({ status: 201, type: UserDto })
  @Post('/')
  async create(
    @Req() req: Request,
    @Body() payload: CreateSetupDto,
  ): Promise<UserDto> {
    const user = await this.setupService.create(payload);
    req.session.userId = user.id;

    return toDto(UserDto, user);
  }

  @Get('/status')
  @ApiOkResponse({ type: StatusDto })
  async status(): Promise<StatusDto> {
    const version = this.configService.getOrThrow<string>('app.version');
    const configured = await this.setupService.status();

    return {
      version,
      configured,
    };
  }
}
