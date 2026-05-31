import { Global, Module } from '@nestjs/common';

import { AuthModule } from 'src/auth/auth.module';
import { DnsModule } from 'src/dns/dns.module';
import { ServerModule } from 'src/server/server.module';
import { SettingsCoreModule } from 'src/settings/core/settings-core.module';
import { SslModule } from 'src/ssl/ssl.module';
import { UsersModule } from 'src/users/users.module';

import { NetworkController } from './network.controller';
import { NetworkService } from './network.service';

@Global()
@Module({
  imports: [
    AuthModule,
    UsersModule,
    DnsModule,
    SslModule,
    ServerModule,
    SettingsCoreModule,
  ],
  controllers: [NetworkController],
  providers: [NetworkService],
  exports: [NetworkService],
})
export class NetworkModule {}
