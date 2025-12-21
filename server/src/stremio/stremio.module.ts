import { Module } from '@nestjs/common';

import { AuthModule } from 'src/auth/auth.module';
import { SettingsCoreModule } from 'src/settings/core/settings-core.module';

import { StremioStreamModule } from './stream/stream.module';
import { StremioController } from './stremio.controller';
import { StremioService } from './stremio.service';

@Module({
  imports: [AuthModule, StremioStreamModule, SettingsCoreModule],
  controllers: [StremioController],
  providers: [StremioService],
})
export class StremioModule {}
