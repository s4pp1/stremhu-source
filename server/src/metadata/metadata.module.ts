import { Module } from '@nestjs/common';

import { SettingsModule } from 'src/settings/settings.module';

import { MetadataController } from './metadata.controller';

@Module({
  imports: [SettingsModule],
  controllers: [MetadataController],
})
export class MetadataModule {}
