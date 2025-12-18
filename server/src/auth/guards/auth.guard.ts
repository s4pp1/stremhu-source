import {
  CanActivate,
  ExecutionContext,
  Injectable,
  UnauthorizedException,
} from '@nestjs/common';
import { Reflector } from '@nestjs/core';
import { Request } from 'express';

import { UsersStore } from 'src/users/core/users.store';
import { User } from 'src/users/entity/user.entity';

import { OPTIONAL_AUTH_KEY } from '../decorators/optional-auth.decorator';

@Injectable()
export class AuthGuard implements CanActivate {
  constructor(
    private usersStore: UsersStore,
    private reflector: Reflector,
  ) {}

  async canActivate(context: ExecutionContext): Promise<boolean> {
    const request = context.switchToHttp().getRequest<Request>();

    const optional = this.reflector.getAllAndOverride<boolean>(
      OPTIONAL_AUTH_KEY,
      [context.getHandler(), context.getClass()],
    );

    const { userId } = request.session;

    let user: User | null = null;

    if (userId) {
      user = await this.usersStore.findOneById(userId);
    }

    if (!user && !optional) {
      throw new UnauthorizedException('Kérjük, jelentkezz be a folytatáshoz.');
    }

    request['user'] = user;
    return true;
  }
}
