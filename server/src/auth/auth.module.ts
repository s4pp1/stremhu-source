import { Module } from '@nestjs/common';

import { UsersCoreModule } from 'src/users/core/users-core.module';

import { AuthController } from './auth.controller';
import { AuthService } from './auth.service';
import { AuthGuard } from './guards/auth.guard';
import { RolesGuard } from './guards/roles.guard';
import { TokenGuard } from './guards/token.guard';

@Module({
  imports: [UsersCoreModule],
  providers: [AuthService, AuthGuard, RolesGuard, TokenGuard],
  controllers: [AuthController],
  exports: [AuthService, AuthGuard, RolesGuard, TokenGuard, UsersCoreModule],
})
export class AuthModule {}
