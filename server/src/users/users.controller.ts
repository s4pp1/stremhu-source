import {
  Body,
  Controller,
  Delete,
  ForbiddenException,
  Get,
  Param,
  ParseUUIDPipe,
  Post,
  Put,
  Req,
  UseGuards,
} from '@nestjs/common';
import { ApiResponse, ApiTags } from '@nestjs/swagger';
import type { Request } from 'express';

import { Roles } from 'src/auth/decorators/roles.decorator';
import { AuthGuard } from 'src/auth/guards/auth.guard';
import { RolesGuard } from 'src/auth/guards/roles.guard';
import { toDto } from 'src/common/utils/to-dto';

import { ChangePasswordDto } from './dto/change-password';
import { ChangeUsernameDto } from './dto/change-username';
import { CreateUserDto } from './dto/create-user.dto';
import { UpdateUserDto } from './dto/update-user.dto';
import { UserDto } from './dto/user.dto';
import { UserRoleEnum } from './enum/user-role.enum';
import { UsersService } from './users.service';

@UseGuards(AuthGuard, RolesGuard)
@Roles(UserRoleEnum.ADMIN)
@Controller('/users')
@ApiTags('Users')
export class UsersController {
  constructor(private usersService: UsersService) {}

  @ApiResponse({ status: 201, type: UserDto })
  @Post('/')
  async create(@Body() payload: CreateUserDto): Promise<UserDto> {
    const user = await this.usersService.create({
      ...payload,
      userRole: UserRoleEnum.USER,
    });

    return user;
  }

  @ApiResponse({ status: 200, type: UserDto, isArray: true })
  @Get('/')
  async find(): Promise<UserDto[]> {
    const users = await this.usersService.find();
    return users.map((user) => toDto(UserDto, user));
  }

  @ApiResponse({ status: 200, type: UserDto })
  @Get('/:userId')
  async findOne(
    @Param('userId', new ParseUUIDPipe()) userId: string,
  ): Promise<UserDto> {
    const user = await this.usersService.findOneOrThrow((qb) =>
      qb.where('id = :userId', { userId }),
    );
    return toDto(UserDto, user);
  }

  @ApiResponse({ status: 200, type: UserDto })
  @Put('/:userId')
  async updateOne(
    @Req() req: Request,
    @Param('userId', new ParseUUIDPipe()) userId: string,
    @Body() payload: UpdateUserDto,
  ): Promise<UserDto> {
    const { id, userRole } = req.user || {};
    if (id === userId && userRole !== payload.userRole) {
      throw new ForbiddenException(
        'Saját fiókod jogosultságát nem módosíthatod!',
      );
    }

    const updatedUser = await this.usersService.updateOneOrThrow(
      userId,
      payload,
    );
    return toDto(UserDto, updatedUser);
  }

  @ApiResponse({ status: 200, type: UserDto })
  @Put('/:userId/username')
  async changeUsername(
    @Param('userId', new ParseUUIDPipe()) userId: string,
    @Body() payload: ChangeUsernameDto,
  ): Promise<UserDto> {
    const user = await this.usersService.updateUsernameOrThrow(
      userId,
      payload.username,
    );
    return toDto(UserDto, user);
  }

  @ApiResponse({ status: 200, type: UserDto })
  @Put('/:userId/password')
  async changePassword(
    @Param('userId', new ParseUUIDPipe()) userId: string,
    @Body() payload: ChangePasswordDto,
  ): Promise<UserDto> {
    const user = await this.usersService.updateOneOrThrow(userId, payload);
    return toDto(UserDto, user);
  }

  @ApiResponse({ status: 200, type: UserDto })
  @Put('/:userId/stremio-token')
  async changeStremioToken(
    @Param('userId', new ParseUUIDPipe()) userId: string,
  ): Promise<UserDto> {
    const user = await this.usersService.regenerateStremioToken(userId);
    return toDto(UserDto, user);
  }

  @ApiResponse({ status: 200 })
  @Delete('/:userId')
  async deleteOne(
    @Req() req: Request,
    @Param('userId', new ParseUUIDPipe()) userId: string,
  ): Promise<void> {
    if (req.user!.id === userId) {
      throw new ForbiddenException('Saját fiókod törlésére nincs lehetőség!');
    }

    await this.usersService.deleteOrThrow(userId);
  }
}
