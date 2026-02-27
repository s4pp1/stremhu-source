import { Module } from '@nestjs/common';

import { KodiStreamsModule } from './streams/kodi-streams.module';

@Module({
  imports: [KodiStreamsModule],
})
export class KodiModule {}
