import {
  ClassSerializerInterceptor,
  INestApplication,
  ValidationPipe,
} from '@nestjs/common';
import { Reflector } from '@nestjs/core';
import { Test, TestingModule } from '@nestjs/testing';
import request from 'supertest';

import { AuthGuard } from 'src/auth/guards/auth.guard';
import { RolesGuard } from 'src/auth/guards/roles.guard';

import { TorrentsCacheController } from '../torrents-cache.controller';
import { TorrentsCacheService } from '../torrents-cache.service';

// Mocking TorrentsCacheService
jest.mock('../torrents-cache.service', () => ({
  TorrentsCacheService: jest.fn().mockImplementation(() => ({
    runRetentionCleanup: jest.fn(),
  })),
}));

describe('TorrentsCache (Integration)', () => {
  let app: INestApplication;

  const mockTorrentsCacheService = {
    runRetentionCleanup: jest.fn().mockResolvedValue(undefined),
  };

  beforeAll(async () => {
    const moduleFixture: TestingModule = await Test.createTestingModule({
      controllers: [TorrentsCacheController],
      providers: [
        {
          provide: TorrentsCacheService,
          useValue: mockTorrentsCacheService,
        },
      ],
    })
      .overrideGuard(AuthGuard)
      .useValue({ canActivate: () => true })
      .overrideGuard(RolesGuard)
      .useValue({ canActivate: () => true })
      .compile();

    app = moduleFixture.createNestApplication();

    app.useGlobalPipes(
      new ValidationPipe({ whitelist: true, transform: true }),
    );

    app.useGlobalInterceptors(
      new ClassSerializerInterceptor(app.get(Reflector)),
    );

    await app.init();
  });

  afterAll(async () => {
    if (app) {
      await app.close();
    }
  });

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('TorrentsCacheController', () => {
    it('/cleanup (POST)', async () => {
      // eslint-disable-next-line @typescript-eslint/no-unsafe-argument
      await request(app.getHttpServer())
        .post('/torrents/cache/cleanup')
        .expect(201);

      expect(mockTorrentsCacheService.runRetentionCleanup).toHaveBeenCalledWith(
        0,
      );
    });
  });
});
