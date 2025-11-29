import { Module } from '@nestjs/common';
import { APP_INTERCEPTOR } from '@nestjs/core';

import { AppFeaturesModule } from './app-features.module';
import { AppInfrastructureModule } from './app-infrastructure.module';
import { AppController } from './app.controller';
import { LoggingInterceptor } from './common/interceptors/logging.interceptor';

@Module({
  controllers: [AppController],
  imports: [AppInfrastructureModule, AppFeaturesModule],
  providers: [
    {
      provide: APP_INTERCEPTOR,
      useClass: LoggingInterceptor,
    },
  ],
})
export class AppModule {}
