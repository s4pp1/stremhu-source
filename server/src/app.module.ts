import { Module } from '@nestjs/common';
import { ConfigModule, ConfigService } from '@nestjs/config';
import { APP_INTERCEPTOR } from '@nestjs/core';
import { ScheduleModule } from '@nestjs/schedule';
import { ServeStaticModule } from '@nestjs/serve-static';
import { TypeOrmModule } from '@nestjs/typeorm';
import { Database } from 'better-sqlite3';
import { join } from 'path';

import { AuthModule } from './auth/auth.module';
import { CatalogClientModule } from './catalog-client/catalog-client.module';
import { LoggingInterceptor } from './common/interceptors/logging.interceptor';
import appConfig from './config/app.config';
import authConfig from './config/auth.config';
import databaseConfig from './config/database.config';
import trackerConfig from './config/tracker.config';
import webTorrentConfig from './config/web-torrent.config';
import { LocalIpModule } from './local-ip/local-ip.module';
import { ReferenceDataModule } from './reference-data/reference-data.module';
import { SessionsModule } from './sessions/sessions.module';
import { SettingsModule } from './settings/settings.module';
import { StremioModule } from './stremio/stremio.module';
import { TorrentCacheModule } from './torrent-cache/torrent-cache.module';
import { TrackersModule } from './trackers/trackers.module';
import { UsersModule } from './users/users.module';
import { WebTorrentModule } from './web-torrent/web-torrent.module';

@Module({
  imports: [
    ConfigModule.forRoot({
      isGlobal: true,
      load: [
        appConfig,
        authConfig,
        databaseConfig,
        webTorrentConfig,
        trackerConfig,
      ],
    }),
    ServeStaticModule.forRootAsync({
      imports: [ConfigModule],
      inject: [ConfigService],
      useFactory: (cfg: ConfigService) => [
        {
          rootPath: cfg.getOrThrow<string>('app.client-path'),
          exclude: ['/api/{*test}'],
          serveStaticOptions: {
            fallthrough: true,
          },
        },
      ],
    }),
    TypeOrmModule.forRootAsync({
      imports: [ConfigModule],
      inject: [ConfigService],
      useFactory: (cfg: ConfigService) => ({
        type: 'better-sqlite3',
        database: cfg.getOrThrow<string>('database.db-path'),
        entities: [join(__dirname, '**/*.entity.{ts,js}')],
        prepareDatabase: (db: Database) => {
          db.exec('PRAGMA journal_mode = WAL;');
          db.exec('PRAGMA synchronous = NORMAL;');
          db.exec('PRAGMA foreign_keys = ON;');
        },
        migrations: [join(__dirname, '@migrations/*.{ts,js}')],
        migrationsTableName: 'migrations',
        migrationsRun: true,
        synchronize: false,
      }),
    }),
    ScheduleModule.forRoot(),
    SettingsModule,
    LocalIpModule,
    AuthModule,
    SessionsModule,
    UsersModule,
    ReferenceDataModule,
    TorrentCacheModule,
    WebTorrentModule,
    TrackersModule,
    StremioModule,
    CatalogClientModule,
  ],
  providers: [
    {
      provide: APP_INTERCEPTOR,
      useClass: LoggingInterceptor,
    },
  ],
})
export class AppModule {}
