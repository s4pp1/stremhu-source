import { Module } from '@nestjs/common';

import { SettingsModule } from 'src/settings/settings.module';
import { TrackersModule } from 'src/trackers/trackers.module';

import { MetadataController } from './metadata.controller';
import { MetadataService } from './metadata.service';
import { PreferencesMetadataService } from './preferences-metadata.service';

@Module({
  imports: [SettingsModule, TrackersModule],
  providers: [MetadataService, PreferencesMetadataService],
  controllers: [MetadataController],
  exports: [MetadataService, PreferencesMetadataService],
})
export class MetadataModule {}
