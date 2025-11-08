import { Module } from '@nestjs/common';

import { TrackerCredentialsModule } from 'src/trackers/credentials/tracker-credentials.module';

import { NcoreAdapter } from './ncore.adapter';
import { NcoreClient } from './ncore.client';
import { NcoreClientFactory } from './ncore.client-factory';

@Module({
  imports: [TrackerCredentialsModule],
  providers: [NcoreAdapter, NcoreClient, NcoreClientFactory],
  exports: [NcoreAdapter],
})
export class NcoreModule {}
