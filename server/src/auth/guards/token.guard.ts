import {
  CanActivate,
  ExecutionContext,
  Injectable,
  UnauthorizedException,
} from '@nestjs/common';
import { isUUID } from 'class-validator';
import { Request } from 'express';

import { UsersStore } from 'src/users/core/users.store';

@Injectable()
export class TokenGuard implements CanActivate {
  constructor(private readonly usersStore: UsersStore) {}

  async canActivate(ctx: ExecutionContext): Promise<boolean> {
    const req = ctx.switchToHttp().getRequest<Request>();
    const token = req.params?.token;

    const isUuid = isUUID(token, '4');

    if (!token || !isUuid) {
      throw new UnauthorizedException(
        'A kulcs érvénytelen vagy nincs megadva!',
      );
    }

    const user = await this.usersStore.findOne((qb) =>
      qb.where('user.token = :token', { token }),
    );

    if (!user) {
      throw new UnauthorizedException('A kulcs érvénytelen!');
    }

    req.user = user;
    return true;
  }
}
