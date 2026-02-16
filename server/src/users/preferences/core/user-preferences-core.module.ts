import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';

import { UserPreference } from '../entity/user-preference.entity';
import { UserPreferencesStore } from './user-preferences.store';

@Module({
  imports: [TypeOrmModule.forFeature([UserPreference])],
  providers: [UserPreferencesStore],
  exports: [UserPreferencesStore],
})
export class UserPreferencesCoreModule {}
