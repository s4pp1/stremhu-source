import { Module } from '@nestjs/common';

import { ManifestModule } from './manifest/manifest.module';
import { PlaybackModule } from './playback/playback.module';
import { StreamsModule } from './streams/streams.module';

@Module({
  imports: [ManifestModule, StreamsModule, PlaybackModule],
})
export class StremioModule {}
