import { Module } from '@nestjs/common';
import { ConfigModule, ConfigService } from '@nestjs/config';
import { ScheduleModule } from '@nestjs/schedule';
import { ServeStaticModule } from '@nestjs/serve-static';
import { TypeOrmModule } from '@nestjs/typeorm';
import { Database } from 'better-sqlite3';
import { join } from 'path';

import appConfig from './config/app.config';
import authConfig from './config/auth.config';
import databaseConfig from './config/database.config';
import torrentConfig from './config/torrent.config';
import trackerConfig from './config/tracker.config';

@Module({
  imports: [
    ConfigModule.forRoot({
      isGlobal: true,
      load: [
        appConfig,
        authConfig,
        databaseConfig,
        torrentConfig,
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
  ],
})
export class AppInfrastructureModule {}
