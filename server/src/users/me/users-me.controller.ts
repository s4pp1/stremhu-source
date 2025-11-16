import { Body, Controller, Get, Put, Req, UseGuards } from '@nestjs/common';
import { ApiResponse, ApiTags } from '@nestjs/swagger';
import type { Request } from 'express';

import { AuthGuard, OptionalAuth } from 'src/auth/guards/auth.guard';
import { toDto } from 'src/common/utils/to-dto';

import { ChangePasswordDto } from '../dto/change-password';
import { ChangeUsernameDto } from '../dto/change-username';
import { UserDto } from '../dto/user.dto';
import { UsersService } from '../users.service';
import { MeUserDto } from './dto/me-user.dto';
import { UpdateMePreferencesDto } from './dto/update-me-preferences';

@ApiTags('Me')
@UseGuards(AuthGuard)
@Controller('/me')
export class UsersMeController {
  constructor(private usersService: UsersService) {}

  @ApiResponse({
    status: 200,
    type: MeUserDto,
  })
  @OptionalAuth()
  @Get('/')
  me(@Req() req: Request): MeUserDto {
    return { me: req.user ? toDto(UserDto, req.user) : null };
  }

  @ApiResponse({ status: 200, type: UserDto })
  @Put('/preferences')
  async updateMe(
    @Req() req: Request,
    @Body() payload: UpdateMePreferencesDto,
  ): Promise<UserDto> {
    const user = await this.usersService.updateOneOrThrow(
      req.user!.id,
      payload,
    );
    return toDto(UserDto, user);
  }

  @ApiResponse({ status: 201, type: UserDto })
  @Put('/username')
  async changeUsername(
    @Req() req: Request,
    @Body() payload: ChangeUsernameDto,
  ): Promise<UserDto> {
    const user = await this.usersService.updateUsernameOrThrow(
      req.user!.id,
      payload.username,
    );
    return toDto(UserDto, user);
  }

  @ApiResponse({ status: 201, type: UserDto })
  @Put('/password')
  async changePassword(
    @Req() req: Request,
    @Body() payload: ChangePasswordDto,
  ): Promise<UserDto> {
    const user = await this.usersService.updateOneOrThrow(
      req.user!.id,
      payload,
    );
    return toDto(UserDto, user);
  }

  @ApiResponse({ status: 201, type: UserDto })
  @Put('/stremio-token')
  async changeStremioToken(@Req() req: Request): Promise<UserDto> {
    const user = await this.usersService.regenerateStremioToken(req.user!.id);
    return toDto(UserDto, user);
  }
}
