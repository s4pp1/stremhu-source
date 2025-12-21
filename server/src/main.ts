import { ValidationPipe } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { NestFactory } from '@nestjs/core';
import { ExpressAdapter } from '@nestjs/platform-express';
import { DocumentBuilder, SwaggerModule } from '@nestjs/swagger';
import express from 'express';
import session from 'express-session';
import { mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';

import { THIRTY_DAYS_MS } from './app.constant';
import { AppModule } from './app.module';
import { NodeEnvEnum } from './config/enum/node-env.enum';
import { SessionsService } from './sessions/sessions.service';

export const EXPRESS = express();

async function bootstrap() {
  const app = await NestFactory.create(AppModule, new ExpressAdapter(EXPRESS));

  const configService = app.get(ConfigService);

  const port = configService.getOrThrow<number>('app.http-port');
  const nodeEnv = configService.getOrThrow<NodeEnvEnum>('app.node-env');
  const secret = configService.getOrThrow<string>('auth.session-secret');
  const openapiDir = configService.getOrThrow<string>('app.openapi-dir');

  const isProduction = nodeEnv === NodeEnvEnum.PRODUCTION;

  app.enableShutdownHooks();

  app.enableCors({ origin: true, credentials: true });

  app.setGlobalPrefix('api');

  const store = app.get(SessionsService);

  app.use(
    session({
      store,
      secret,
      resave: false,
      saveUninitialized: false,
      rolling: true,
      proxy: isProduction,
      name: 'stremhu.source',
      cookie: {
        httpOnly: true,
        sameSite: 'lax',
        maxAge: THIRTY_DAYS_MS,
        path: '/',
      },
    }),
  );

  if (!isProduction) {
    const config = new DocumentBuilder()
      .setTitle('StremHU')
      .setDescription('REST API dokumentáció')
      .setVersion('1.0.0')
      .build();

    const document = SwaggerModule.createDocument(app, config, {
      operationIdFactory: (_controllerKey, methodKey) => methodKey,
    });
    SwaggerModule.setup('api/docs', app, document);

    await mkdir(openapiDir, { recursive: true });

    await writeFile(
      path.join(openapiDir, 'openapi.json'),
      JSON.stringify(document, null, 2),
    );
  }

  app.useGlobalPipes(
    new ValidationPipe({
      whitelist: true,
      transform: true,
    }),
  );

  await app.init();

  await new Promise<void>((resolve) => {
    EXPRESS.listen(port, () => resolve());
  });
}

bootstrap().catch((error) => {
  console.error(error);
});
