import { Module } from '@nestjs/common';

import { SettingsModule } from 'src/settings/settings.module';
import { TrackersModule } from 'src/trackers/trackers.module';

import { MetadataController } from './metadata.controller';

@Module({
  imports: [SettingsModule, TrackersModule],
  controllers: [MetadataController],
})
export class MetadataModule {}
