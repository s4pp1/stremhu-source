import { HttpException, Injectable } from '@nestjs/common';
import { EntityManager } from 'typeorm';

import { UserRoleEnum } from 'src/users/enum/user-role.enum';
import { UsersService } from 'src/users/users.service';

import { SettingsStore } from '../core/settings.store';
import { CreateSetupDto } from './dto/create-setup.dto';
import { StatusDto } from './dto/status.dto';

@Injectable()
export class SetupService {
  constructor(
    private readonly usersService: UsersService,
    private readonly settingsStore: SettingsStore,
  ) {}

  async create(payload: CreateSetupDto, manager?: EntityManager) {
    const users = await this.usersService.find();

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
    const users = await this.usersService.find((qb) =>
      qb.where('user_role = :userRole', { userRole: UserRoleEnum.ADMIN }),
    );
    const setting = await this.settingsStore.findOneOrThrow();

    const hasAdminUser = users.length > 0;

    return {
      hasAdminUser,
      hasAddress: setting.address !== null,
    };
  }
}
