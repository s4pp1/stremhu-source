import { Module } from '@nestjs/common';

import { UserPreferencesCoreModule } from './core/user-preferences-core.module';
import { UserPreferencesService } from './user-preferences.service';

@Module({
  imports: [UserPreferencesCoreModule],
  providers: [UserPreferencesService],
  controllers: [],
  exports: [UserPreferencesService],
})
export class UserPreferencesModule {}
