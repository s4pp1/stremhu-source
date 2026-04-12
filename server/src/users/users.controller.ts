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
  SerializeOptions,
  UseGuards,
} from '@nestjs/common';
import { ApiTags } from '@nestjs/swagger';
import type { Request } from 'express';

import { Roles } from 'src/auth/decorators/roles.decorator';
import { AuthGuard } from 'src/auth/guards/auth.guard';
import { RolesGuard } from 'src/auth/guards/roles.guard';

import { UsersStore } from './core/users.store';
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
  constructor(
    private readonly usersStore: UsersStore,
    private readonly usersService: UsersService,
  ) {}

  @SerializeOptions({ type: UserDto })
  @Post('/')
  async create(@Body() payload: CreateUserDto): Promise<UserDto> {
    const user = await this.usersService.create({
      ...payload,
      userRole: UserRoleEnum.USER,
    });

    return user;
  }

  @SerializeOptions({ type: UserDto })
  @Get('/')
  async find(): Promise<UserDto[]> {
    const users = await this.usersStore.find();

    return users;
  }

  @SerializeOptions({ type: UserDto })
  @Get('/:userId')
  async findOne(
    @Param('userId', new ParseUUIDPipe()) userId: string,
  ): Promise<UserDto> {
    const user = await this.usersStore.findOneByIdOrThrow(userId);

    return user;
  }

  @SerializeOptions({ type: UserDto })
  @Put('/:userId')
  async updateOne(
    @Req() req: Request,
    @Param('userId', new ParseUUIDPipe()) userId: string,
    @Body() payload: UpdateUserDto,
  ): Promise<UserDto> {
    const { id, userRole } = req.user!;

    if (
      id === userId &&
      payload.userRole !== undefined &&
      userRole !== payload.userRole
    ) {
      throw new ForbiddenException(
        'Saját fiókod jogosultságát nem módosíthatod!',
      );
    }

    const updatedUser = await this.usersService.updateOrThrow(userId, payload);

    return updatedUser;
  }

  @SerializeOptions({ type: UserDto })
  @Put('/:userId/token/regenerate')
  async regenerateToken(
    @Param('userId', new ParseUUIDPipe()) userId: string,
  ): Promise<UserDto> {
    const user = await this.usersService.regenerateToken(userId);

    return user;
  }

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
