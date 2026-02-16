import { Module } from '@nestjs/common';

import { UsersCoreModule } from '../core/users-core.module';
import { UserPreferencesCoreModule } from './core/user-preferences-core.module';
import { UserPreferencesController } from './user-preferences.controller';
import { UserPreferencesService } from './user-preferences.service';

@Module({
  imports: [UsersCoreModule, UserPreferencesCoreModule],
  providers: [UserPreferencesService],
  controllers: [UserPreferencesController],
  exports: [UserPreferencesService],
})
export class UserPreferencesModule {}
