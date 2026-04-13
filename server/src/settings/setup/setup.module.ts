import { Module } from '@nestjs/common';

import { UsersCoreModule } from 'src/users/core/users-core.module';
import { UsersModule } from 'src/users/users.module';

import { SettingsCoreModule } from '../core/settings-core.module';
import { SetupController } from './setup.controller';
import { SetupService } from './setup.service';

@Module({
  imports: [UsersCoreModule, UsersModule, SettingsCoreModule],
  providers: [SetupService],
  controllers: [SetupController],
})
export class SetupModule {}
