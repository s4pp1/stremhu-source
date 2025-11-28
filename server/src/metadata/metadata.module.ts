import { Module } from '@nestjs/common';

import { SettingsCoreModule } from 'src/settings/core/settings-core.module';

import { MetadataController } from './metadata.controller';

@Module({
  imports: [SettingsCoreModule],
  controllers: [MetadataController],
})
export class MetadataModule {}
