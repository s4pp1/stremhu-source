import { Module } from '@nestjs/common';

import { AuthModule } from 'src/auth/auth.module';
import { UserPreferencesModule } from 'src/users/preferences/user-preferences.module';

import { UsersModule } from '../users/users.module';
import { MeController } from './me.controller';
import { MePreferencesController } from './preferences/me-preferences.controller';

@Module({
  imports: [AuthModule, UsersModule, UserPreferencesModule],
  controllers: [MeController, MePreferencesController],
})
export class MeModule {}
