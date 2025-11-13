import {
  CanActivate,
  ExecutionContext,
  Injectable,
  UnauthorizedException,
} from '@nestjs/common';
import { Request } from 'express';

import { UsersService } from 'src/users/users.service';

@Injectable()
export class StremioTokenGuard implements CanActivate {
  constructor(private readonly usersService: UsersService) {}

  async canActivate(ctx: ExecutionContext): Promise<boolean> {
    const req = ctx.switchToHttp().getRequest<Request>();
    const token = req.params?.token;
    if (!token) {
      throw new UnauthorizedException('Hiányzik a Stremio Token!');
    }

    const user = await this.usersService.findOne((qb) =>
      qb.where('stremio_token = :token', { token }),
    );

    if (!user) {
      throw new UnauthorizedException('Érvénytelen Stremio Token!');
    }

    req.user = user;
    return true;
  }
}
