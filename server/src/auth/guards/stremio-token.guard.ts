import {
  CanActivate,
  ExecutionContext,
  Injectable,
  UnauthorizedException,
} from '@nestjs/common';
import { isUUID } from 'class-validator';
import { Request } from 'express';

import { UsersService } from 'src/users/users.service';

@Injectable()
export class StremioTokenGuard implements CanActivate {
  constructor(private readonly usersService: UsersService) {}

  async canActivate(ctx: ExecutionContext): Promise<boolean> {
    const req = ctx.switchToHttp().getRequest<Request>();
    const token = req.params?.token;

    const isUuid = isUUID(token, '4');

    if (!token || !isUuid) {
      throw new UnauthorizedException(
        'A kulcs érvénytelen vagy nincs megadva!',
      );
    }

    const user = await this.usersService.findOne((qb) =>
      qb.where('stremio_token = :token', { token }),
    );

    if (!user) {
      throw new UnauthorizedException('A kulcs érvénytelen!');
    }

    req.user = user;
    return true;
  }
}
