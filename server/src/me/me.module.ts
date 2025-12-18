import { Module } from '@nestjs/common';

import { AuthModule } from 'src/auth/auth.module';

import { UsersModule } from '../users/users.module';
import { MeController } from './me.controller';

@Module({
  imports: [AuthModule, UsersModule],
  controllers: [MeController],
})
export class MeModule {}
