import {
  ClassSerializerInterceptor,
  INestApplication,
  ValidationPipe,
} from '@nestjs/common';
import { Reflector } from '@nestjs/core';
import { Test, TestingModule } from '@nestjs/testing';
import request from 'supertest';

import { PairingsCoreService } from '../../core/pairings-core.service';
import { PairingsIntegrationController } from '../pairings-integration.controller';

// Mocking PairingsCoreService
jest.mock('../../core/pairings-core.service', () => ({
  PairingsCoreService: jest.fn().mockImplementation(() => ({
    generatePairingCodes: jest.fn(),
    pollPairingStatus: jest.fn(),
    authorizePairingCode: jest.fn(),
  })),
}));

describe('Pairings Integration (Integration)', () => {
  let app: INestApplication;

  const mockDeviceCode = '123e4567-e89b-12d3-a456-426614174000';
  const mockPairInit = {
    deviceCode: mockDeviceCode,
    userCode: '1234',
  };
  const mockPairStatus = {
    status: 'pending',
  };

  const mockPairingsService = {
    generatePairingCodes: jest.fn().mockResolvedValue(mockPairInit),
    pollPairingStatus: jest.fn().mockResolvedValue(mockPairStatus),
    authorizePairingCode: jest.fn(),
  };

  beforeAll(async () => {
    const moduleFixture: TestingModule = await Test.createTestingModule({
      controllers: [PairingsIntegrationController],
      providers: [
        {
          provide: PairingsCoreService,
          useValue: mockPairingsService,
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

  describe('PairingsIntegrationController', () => {
    it('/init (POST)', async () => {
      // eslint-disable-next-line @typescript-eslint/no-unsafe-argument
      const response = await request(app.getHttpServer())
        .post('/auth/pair/init')
        .expect(201);

      expect(response.body).toEqual(mockPairInit);
      expect(mockPairingsService.generatePairingCodes).toHaveBeenCalled();
    });

    it('/status (POST)', async () => {
      const payload = { deviceCode: mockDeviceCode };
      // eslint-disable-next-line @typescript-eslint/no-unsafe-argument
      const response = await request(app.getHttpServer())
        .post('/auth/pair/status')
        .send(payload)
        .expect(200);

      expect(response.body).toEqual(mockPairStatus);
      expect(mockPairingsService.pollPairingStatus).toHaveBeenCalledWith(
        payload.deviceCode,
      );
    });
  });
});
