import { Module } from '@nestjs/common';

import { UsersModule } from 'src/users/users.module';

import { SettingsCoreModule } from '../core/settings-core.module';
import { SetupController } from './setup.controller';
import { SetupService } from './setup.service';

@Module({
  imports: [UsersModule, SettingsCoreModule],
  providers: [SetupService],
  controllers: [SetupController],
})
export class SetupModule {}
