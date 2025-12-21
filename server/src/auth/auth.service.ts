import { Injectable, NotFoundException } from '@nestjs/common';
import { verify } from '@node-rs/argon2';

import { UsersStore } from 'src/users/core/users.store';

import { USER_NOT_FOUND } from './auth.constants';

@Injectable()
export class AuthService {
  constructor(private usersStore: UsersStore) {}

  async validate(username: string, password: string) {
    const user = await this.usersStore.findOne((qb) =>
      qb.where('user.username = :username', { username }),
    );

    if (!user || !user.passwordHash) {
      throw new NotFoundException(USER_NOT_FOUND);
    }

    const validated = await verify(user.passwordHash, password);

    if (!validated) {
      throw new NotFoundException(USER_NOT_FOUND);
    }

    return user;
  }
}
