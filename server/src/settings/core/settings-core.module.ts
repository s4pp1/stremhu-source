import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';

import { Setting } from '../entity/setting.entity';
import { SettingsStore } from './settings.store';

@Module({
  imports: [TypeOrmModule.forFeature([Setting])],
  providers: [SettingsStore],
  exports: [SettingsStore],
})
export class SettingsCoreModule {}
