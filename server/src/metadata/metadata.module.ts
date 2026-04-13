import { Module } from '@nestjs/common';

import { SettingsCoreModule } from 'src/settings/core/settings-core.module';
import { TrackersMetaModule } from 'src/trackers/meta/trackers-meta.module';
import { TrackersModule } from 'src/trackers/trackers.module';

import { MetadataController } from './metadata.controller';
import { MetadataService } from './metadata.service';
import { PreferencesMetadataService } from './preferences-metadata.service';

@Module({
  imports: [SettingsCoreModule, TrackersModule, TrackersMetaModule],
  providers: [MetadataService, PreferencesMetadataService],
  controllers: [MetadataController],
  exports: [MetadataService, PreferencesMetadataService],
})
export class MetadataModule {}
