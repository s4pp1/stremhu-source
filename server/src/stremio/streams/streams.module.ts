import { Module } from '@nestjs/common';

import { AuthModule } from 'src/auth/auth.module';
import { CatalogModule } from 'src/catalog/catalog.module';
import { SettingsCoreModule } from 'src/settings/core/settings-core.module';
import { TrackersModule } from 'src/trackers/trackers.module';

import { StreamsController } from './streams.controller';
import { StreamsService } from './streams.service';

@Module({
  imports: [AuthModule, SettingsCoreModule, TrackersModule, CatalogModule],
  providers: [StreamsService],
  controllers: [StreamsController],
})
export class StreamsModule {}
