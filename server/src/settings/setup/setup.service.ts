import { HttpException, Injectable } from '@nestjs/common';
import { EntityManager } from 'typeorm';

import { UsersStore } from 'src/users/core/users.store';
import { UserRoleEnum } from 'src/users/enum/user-role.enum';
import { UsersService } from 'src/users/users.service';

import { AppSettingsService } from '../app/app-settings.service';
import { CreateSetupDto } from './dto/create-setup.dto';
import { StatusDto } from './dto/status.dto';

@Injectable()
export class SetupService {
  constructor(
    private readonly usersStore: UsersStore,
    private readonly usersService: UsersService,
    private readonly appSettingsService: AppSettingsService,
  ) {}

  async create(payload: CreateSetupDto, manager?: EntityManager) {
    const users = await this.usersStore.find();

    if (users.length > 0) {
      throw new HttpException('Szerver már kofigurálva van', 410);
    }

    const user = await this.usersService.create(
      {
        ...payload,
        userRole: UserRoleEnum.ADMIN,
      },
      manager,
    );

    return user;
  }

  async status(): Promise<StatusDto> {
    const users = await this.usersStore.find((qb) =>
      qb.where('user.userRole = :userRole', { userRole: UserRoleEnum.ADMIN }),
    );
    const setting = await this.appSettingsService.get();

    const hasAdminUser = users.length > 0;

    return {
      hasAdminUser,
      hasAddress: setting.address !== null,
    };
  }
}
