import {
  ClassSerializerInterceptor,
  INestApplication,
  ValidationPipe,
} from '@nestjs/common';
import { Reflector } from '@nestjs/core';
import { Test, TestingModule } from '@nestjs/testing';
import request from 'supertest';

import { CatalogController } from '../catalog.controller';
import { CatalogService } from '../catalog.service';

// Mocking CatalogService
jest.mock('../catalog.service', () => ({
  CatalogService: jest.fn().mockImplementation(() => ({
    catalogHealthCheck: jest.fn(),
  })),
}));

describe('Catalog (Integration)', () => {
  let app: INestApplication;

  const mockHealth = {
    status: 'ok',
  };

  const mockCatalogService = {
    catalogHealthCheck: jest.fn().mockResolvedValue(mockHealth),
  };

  beforeAll(async () => {
    const moduleFixture: TestingModule = await Test.createTestingModule({
      controllers: [CatalogController],
      providers: [
        {
          provide: CatalogService,
          useValue: mockCatalogService,
        },
      ],
    }).compile();

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

  describe('CatalogController', () => {
    it('/health (GET)', async () => {
      // eslint-disable-next-line @typescript-eslint/no-unsafe-argument
      const response = await request(app.getHttpServer())
        .get('/catalog/health')
        .expect(200);

      expect(response.body).toEqual(mockHealth);
      expect(mockCatalogService.catalogHealthCheck).toHaveBeenCalled();
    });
  });
});
