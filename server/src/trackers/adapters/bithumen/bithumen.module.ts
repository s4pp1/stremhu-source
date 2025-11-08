import { Module } from '@nestjs/common';

import { TrackerCredentialsModule } from 'src/trackers/credentials/tracker-credentials.module';

import { BithumenAdapter } from './bithumen.adapter';
import { BithumenClient } from './bithumen.client';
import { BithumenClientFactory } from './bithumen.client-factory';

@Module({
  imports: [TrackerCredentialsModule],
  providers: [BithumenAdapter, BithumenClient, BithumenClientFactory],
  exports: [BithumenAdapter],
})
export class BithumenModule {}
