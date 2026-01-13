import { Module } from '@nestjs/common';

import { AuthModule } from 'src/auth/auth.module';
import { SettingsModule } from 'src/settings/settings.module';

import { ManifestController } from './manifest.controller';
import { ManifestService } from './manifest.service';

@Module({
  imports: [AuthModule, SettingsModule],
  controllers: [ManifestController],
  providers: [ManifestService],
})
export class ManifestModule {}
