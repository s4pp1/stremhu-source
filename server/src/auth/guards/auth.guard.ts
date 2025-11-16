import {
  CanActivate,
  ExecutionContext,
  Injectable,
  SetMetadata,
  UnauthorizedException,
} from '@nestjs/common';
import { Reflector } from '@nestjs/core';
import { Request } from 'express';

import { User } from 'src/users/entities/user.entity';
import { UsersService } from 'src/users/users.service';

export const OPTIONAL_AUTH_KEY = 'auth:optional';
export const OptionalAuth = () => SetMetadata(OPTIONAL_AUTH_KEY, true);

@Injectable()
export class AuthGuard implements CanActivate {
  constructor(
    private usersService: UsersService,
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
      user = await this.usersService.findOne((qb) =>
        qb.where('id = :userId', { userId }),
      );
    }

    if (!user && !optional) {
      throw new UnauthorizedException('Kérjük, jelentkezz be a folytatáshoz.');
    }

    request['user'] = user;
    return true;
  }
}
