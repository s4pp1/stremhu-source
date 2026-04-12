import {
  ClassSerializerInterceptor,
  INestApplication,
  ValidationPipe,
} from '@nestjs/common';
import { Reflector } from '@nestjs/core';
import { Test, TestingModule } from '@nestjs/testing';
import request from 'supertest';

import { MetadataController } from '../metadata.controller';
import { MetadataService } from '../metadata.service';

// Mocking MetadataService
jest.mock('../metadata.service', () => ({
  MetadataService: jest.fn().mockImplementation(() => ({
    get: jest.fn(),
  })),
}));

describe('Metadata (Integration)', () => {
  let app: INestApplication;

  const mockMetadata = {
    version: '1.0.0',
    trackers: [],
  };

  const mockMetadataService = {
    get: jest.fn().mockResolvedValue(mockMetadata),
  };

  beforeAll(async () => {
    const moduleFixture: TestingModule = await Test.createTestingModule({
      controllers: [MetadataController],
      providers: [
        {
          provide: MetadataService,
          useValue: mockMetadataService,
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

  describe('MetadataController', () => {
    it('/ (GET)', async () => {
      // eslint-disable-next-line @typescript-eslint/no-unsafe-argument
      const response = await request(app.getHttpServer())
        .get('/metadata')
        .expect(200);

      expect(response.body).toEqual(mockMetadata);
      expect(mockMetadataService.get).toHaveBeenCalled();
    });
  });
});
