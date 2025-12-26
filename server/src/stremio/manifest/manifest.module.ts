import { Module } from '@nestjs/common';

import { AuthModule } from 'src/auth/auth.module';
import { SettingsCoreModule } from 'src/settings/core/settings-core.module';

import { ManifestController } from './manifest.controller';
import { ManifestService } from './manifest.service';

@Module({
  imports: [AuthModule, SettingsCoreModule],
  controllers: [ManifestController],
  providers: [ManifestService],
})
export class ManifestModule {}
