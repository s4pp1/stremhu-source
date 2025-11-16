import {
  CanActivate,
  ExecutionContext,
  ForbiddenException,
  Injectable,
  UnauthorizedException,
} from '@nestjs/common';
import { Reflector } from '@nestjs/core';
import { Request } from 'express';

import { UserRoleEnum } from 'src/users/enums/user-role.enum';

import { ROLES_KEY } from '../decorators/roles.decorator';

@Injectable()
export class RolesGuard implements CanActivate {
  constructor(private readonly reflector: Reflector) {}

  canActivate(context: ExecutionContext): boolean {
    const required = this.reflector.getAllAndOverride<UserRoleEnum[]>(
      ROLES_KEY,
      [context.getHandler(), context.getClass()],
    );

    if (!required || required.length === 0) return true;

    const req = context.switchToHttp().getRequest<Request>();
    const { user } = req;

    if (!user) {
      throw new UnauthorizedException('Kérjük, jelentkezz be a folytatáshoz.');
    }

    if (!required.includes(user.userRole)) {
      throw new ForbiddenException('Ehhez a funkcióhoz nincs jogosultságod.');
    }

    return true;
  }
}
