import { Module } from '@nestjs/common';

import { AuthModule } from 'src/auth/auth.module';
import { UserPreferencesModule } from 'src/user-preferences/user-preferences.module';

import { UsersModule } from '../users/users.module';
import { MeController } from './me.controller';

@Module({
  imports: [AuthModule, UsersModule, UserPreferencesModule],
  controllers: [MeController],
})
export class MeModule {}
