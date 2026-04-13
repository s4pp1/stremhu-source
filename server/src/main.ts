import { ClassSerializerInterceptor, ValidationPipe } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { NestFactory, Reflector } from '@nestjs/core';
import { ExpressAdapter } from '@nestjs/platform-express';
import { DocumentBuilder, SwaggerModule } from '@nestjs/swagger';
import express from 'express';
import session from 'express-session';
import { mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';

import { THIRTY_DAYS_MS } from './app.constant';
import { AppModule } from './app.module';
import { NodeEnvEnum } from './config/enum/node-env.enum';
import { KodiStreamsIntegrationModule } from './kodi/streams/integration/kodi-streams-integration.module';
import { PairingsIntegrationModule } from './pairings/integration/pairings-integration.module';
import { PlayIntegrationModule } from './play/integration/play-integration.module';
import { RelaySettingsIntegrationModule } from './relay/settings/integration/relay-settings-integration.module';
import { SessionsService } from './sessions/sessions.service';
import { StremioCatalogsIntegrationModule } from './stremio/catalogs/integration/stremio-catalogs-integration.module';
import { StremioIntegrationModule } from './stremio/integration/stremio-integration.module';
import { StremioStreamsIntegrationModule } from './stremio/streams/integration/stremio-streams-integration.module';

export const EXPRESS = express();

async function bootstrap() {
  process.title = 'stremhu-source';
  const app = await NestFactory.create(AppModule, new ExpressAdapter(EXPRESS));

  const configService = app.get(ConfigService);

  const port = configService.getOrThrow<number>('app.http-port');
  const nodeEnv = configService.getOrThrow<NodeEnvEnum>('app.node-env');
  const secret = configService.getOrThrow<string>('auth.session-secret');
  const openapiDir = configService.getOrThrow<string>('app.openapi-dir');

  const isProd = nodeEnv === NodeEnvEnum.PRODUCTION;

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
      proxy: isProd,
      name: 'stremhu.source',
      cookie: {
        httpOnly: true,
        sameSite: 'lax',
        maxAge: THIRTY_DAYS_MS,
        path: '/',
      },
    }),
  );

  const operationIdFactory = (controllerKey: string, methodKey: string) =>
    `${controllerKey.replace('Controller', '')}${methodKey.charAt(0).toUpperCase() + methodKey.slice(1)}`;

  const integrationsSwagger = new DocumentBuilder()
    .setTitle('StremHU Source - Külső integrációk')
    .setDescription(
      'API külső szolgáltatások számára token alapú hitelesítéssel.',
    )
    .setVersion('1.0.0')
    .build();

  const integrationsSwaggerDoc = SwaggerModule.createDocument(
    app,
    integrationsSwagger,
    {
      operationIdFactory,
      include: [
        StremioIntegrationModule,
        StremioStreamsIntegrationModule,
        StremioCatalogsIntegrationModule,
        KodiStreamsIntegrationModule,
        RelaySettingsIntegrationModule,
        PlayIntegrationModule,
        PairingsIntegrationModule,
      ],
    },
  );
  SwaggerModule.setup('api/docs/integrations', app, integrationsSwaggerDoc);

  if (!isProd) {
    const config = new DocumentBuilder()
      .setTitle('StremHU Source')
      .setDescription('REST API dokumentáció')
      .setVersion('1.0.0')
      .build();

    const document = SwaggerModule.createDocument(app, config, {
      operationIdFactory,
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

  app.useGlobalInterceptors(
    new ClassSerializerInterceptor(app.get(Reflector), {
      excludeExtraneousValues: true,
    }),
  );

  await app.init();

  await new Promise<void>((resolve, reject) => {
    const server = EXPRESS.listen(port);

    server.once('listening', resolve);
    server.once('error', reject);
  });
}

bootstrap().catch((error) => {
  console.error(error);
});
