import { Module } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';

import { RelaySettingsModule } from 'src/settings/relay/relay-settings.module';

import { RelayClient } from './client';
import { RELAY_BASE_URL } from './relay.content';
import { RelayService } from './relay.service';
import { RELAY_CLIENT } from './relay.token';

@Module({
  imports: [RelaySettingsModule],
  providers: [
    {
      provide: RELAY_CLIENT,
      inject: [ConfigService],
      useFactory: () => {
        return new RelayClient({
          BASE: RELAY_BASE_URL,
        });
      },
    },
    RelayService,
  ],
  exports: [RelayService],
})
export class RelayModule {}
