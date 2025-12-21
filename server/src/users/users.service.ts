import { BadRequestException, Injectable } from '@nestjs/common';
import { hash } from '@node-rs/argon2';
import { isUndefined, omitBy } from 'lodash';
import { randomUUID } from 'node:crypto';
import { EntityManager } from 'typeorm';

import { UsersStore } from './core/users.store';
import { UserToCreate } from './type/user-to-create.type';
import { UserToUpdate } from './type/user-to-update.type';

@Injectable()
export class UsersService {
  constructor(private readonly usersStore: UsersStore) {}

  async create(payload: UserToCreate, manager?: EntityManager) {
    await this.checkExistUsername(payload.username);

    const passwordHash = payload.password ? await hash(payload.password) : null;

    const user = await this.usersStore.create(
      {
        ...payload,
        passwordHash,
        token: randomUUID(),
      },
      manager,
    );

    return user;
  }

  async updateOrThrow(
    userId: string,
    payload: UserToUpdate,
    manager?: EntityManager,
  ) {
    const user = await this.usersStore.findOneByIdOrThrow(userId);

    const updateData = omitBy(payload, isUndefined);

    if (payload.username) {
      await this.checkExistUsername(payload.username);
    }

    if (payload.password) {
      const passwordHash = await hash(payload.password);
      delete updateData.password;
      updateData.passwordHash = passwordHash;
    }

    const updatedUser = await this.usersStore.updateOneOrThrow(
      user.id,
      updateData,
      manager,
    );

    return updatedUser;
  }

  async regenerateToken(userId: string, manager?: EntityManager) {
    const user = await this.usersStore.findOneByIdOrThrow(userId);

    const token = randomUUID();

    const updatedUser = await this.usersStore.updateOneOrThrow(
      user.id,
      { token },
      manager,
    );

    return updatedUser;
  }

  async deleteOrThrow(userId: string, manager?: EntityManager) {
    await this.usersStore.deleteOrThrow(userId, manager);
  }

  private async checkExistUsername(username: string) {
    const users = await this.usersStore.find((qb) => {
      qb.where('user.username = :username', {
        username,
      });

      return qb;
    });

    if (users.length !== 0) {
      throw new BadRequestException('A felhasználónév már használatban van.');
    }
  }
}
