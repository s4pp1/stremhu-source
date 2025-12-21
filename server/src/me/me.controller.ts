import { Body, Controller, Get, Put, Req, UseGuards } from '@nestjs/common';
import { ApiResponse, ApiTags } from '@nestjs/swagger';
import type { Request } from 'express';

import { OptionalAuth } from 'src/auth/decorators/optional-auth.decorator';
import { AuthGuard } from 'src/auth/guards/auth.guard';
import { toDto } from 'src/common/utils/to-dto';

import { UserDto } from '../users/dto/user.dto';
import { UsersService } from '../users/users.service';
import { MeDto } from './dto/me.dto';
import { UpdateMeDto } from './dto/update-me.dto';

@ApiTags('Me')
@UseGuards(AuthGuard)
@Controller('/me')
export class MeController {
  constructor(private usersService: UsersService) {}

  @ApiResponse({
    status: 200,
    type: MeDto,
  })
  @OptionalAuth()
  @Get('/')
  me(@Req() req: Request): MeDto {
    return { me: req.user ? toDto(UserDto, req.user) : null };
  }

  @ApiResponse({ status: 200, type: UserDto })
  @Put('/')
  async updateMe(
    @Req() req: Request,
    @Body() payload: UpdateMeDto,
  ): Promise<UserDto> {
    const user = await this.usersService.updateOrThrow(req.user!.id, payload);
    return toDto(UserDto, user);
  }

  @ApiResponse({ status: 201, type: UserDto })
  @Put('/token/regenerate')
  async regenerateToken(@Req() req: Request): Promise<UserDto> {
    const user = await this.usersService.regenerateToken(req.user!.id);
    return toDto(UserDto, user);
  }
}
