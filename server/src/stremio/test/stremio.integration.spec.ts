import {
  ClassSerializerInterceptor,
  INestApplication,
  ValidationPipe,
} from '@nestjs/common';
import { Reflector } from '@nestjs/core';
import { Test, TestingModule } from '@nestjs/testing';
import request from 'supertest';

import { TokenGuard } from '../../auth/guards/token.guard';
import { StremioController } from '../stremio.controller';
import { StremioService } from '../stremio.service';

// Mocking StremioService
jest.mock('../stremio.service', () => ({
  StremioService: jest.fn().mockImplementation(() => ({
    manifest: jest.fn(),
  })),
}));

describe('Stremio (Integration)', () => {
  let app: INestApplication;

  const mockToken = 'mock-token';
  const mockManifest = {
    id: 'stremhu',
    name: 'StremHU',
    version: '1.0.0',
  };

  const mockStremioService = {
    manifest: jest.fn().mockResolvedValue(mockManifest),
  };

  beforeAll(async () => {
    const moduleFixture: TestingModule = await Test.createTestingModule({
      controllers: [StremioController],
      providers: [
        {
          provide: StremioService,
          useValue: mockStremioService,
        },
      ],
    })
      .overrideGuard(TokenGuard)
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

  describe('StremioController', () => {
    it('/configure (GET)', async () => {
      // eslint-disable-next-line @typescript-eslint/no-unsafe-argument
      await request(app.getHttpServer())
        .get(`/${mockToken}/stremio/configure`)
        .expect(308)
        .expect('Location', '/');
    });

    it('/manifest.json (GET)', async () => {
      // eslint-disable-next-line @typescript-eslint/no-unsafe-argument
      const response = await request(app.getHttpServer())
        .get(`/${mockToken}/stremio/manifest.json`)
        .expect(200);

      expect(response.body).toEqual(mockManifest);
      expect(mockStremioService.manifest).toHaveBeenCalled();
    });
  });
});
