import { Module } from '@nestjs/common';

import { UsersCoreModule } from './core/users-core.module';
import { UserPreferencesModule } from './preferences/user-preferences.module';
import { UsersController } from './users.controller';
import { UsersService } from './users.service';

@Module({
  imports: [UsersCoreModule, UserPreferencesModule],
  providers: [UsersService],
  controllers: [UsersController],
  exports: [UsersService],
})
export class UsersModule {}
