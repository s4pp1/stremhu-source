import {
  CanActivate,
  ExecutionContext,
  Injectable,
  UnauthorizedException,
} from '@nestjs/common';
import { Request } from 'express';

import { User } from 'src/users/entities/user.entity';
import { UsersService } from 'src/users/users.service';

@Injectable()
export class AuthGuard implements CanActivate {
  constructor(private usersService: UsersService) {}

  async canActivate(context: ExecutionContext): Promise<boolean> {
    const request = context.switchToHttp().getRequest<Request>();
    const { userId } = request.session;

    let user: User | null = null;

    if (userId) {
      user = await this.usersService.findOne((qb) =>
        qb.where('id = :userId', { userId }),
      );
    }

    if (!user) {
      throw new UnauthorizedException('Kérjük, jelentkezz be a folytatáshoz.');
    }

    request['user'] = user;
    return true;
  }
}
