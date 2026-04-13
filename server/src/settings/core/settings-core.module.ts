import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';

import { Setting } from '../entity/setting.entity';
import { SettingsCoreService } from './settings-core.service';
import { SettingsStore } from './settings.store';

@Module({
  imports: [TypeOrmModule.forFeature([Setting])],
  providers: [SettingsCoreService, SettingsStore],
  exports: [SettingsCoreService],
})
export class SettingsCoreModule {}
