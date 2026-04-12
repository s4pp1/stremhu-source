import {
  ClassSerializerInterceptor,
  ExecutionContext,
  INestApplication,
  ValidationPipe,
} from '@nestjs/common';
import { Reflector } from '@nestjs/core';
import { Test, TestingModule } from '@nestjs/testing';
import { Request } from 'express';
import request from 'supertest';

import { AuthGuard } from '../../auth/guards/auth.guard';
import { User } from '../../users/entity/user.entity';
import { UserRoleEnum } from '../../users/enum/user-role.enum';
import { PairingsController } from '../pairings.controller';
import { PairingsService } from '../pairings.service';

// Mocking PairingsService
jest.mock('../pairings.service', () => ({
  PairingsService: jest.fn().mockImplementation(() => ({
    generatePairingCodes: jest.fn(),
    pollPairingStatus: jest.fn(),
    authorizePairingCode: jest.fn(),
  })),
}));

describe('Pairings (Integration)', () => {
  let app: INestApplication;

  const mockUser: User = {
    id: 'user-id',
    username: 'testuser',
    passwordHash: null,
    token: 'mock-token',
    userRole: UserRoleEnum.USER,
    torrentSeed: null,
    onlyBestTorrent: false,
    updatedAt: new Date('2026-04-12T10:00:00Z'),
    createdAt: new Date('2026-04-12T10:00:00Z'),
  };
  const mockDeviceCode = '123e4567-e89b-12d3-a456-426614174000';
  const mockPairInit = {
    deviceCode: mockDeviceCode,
    userCode: '1234',
  };
  const mockPairStatus = {
    status: 'pending',
  };
  const mockPairVerify = {
    verified: true,
  };

  const mockPairingsService = {
    generatePairingCodes: jest.fn().mockResolvedValue(mockPairInit),
    pollPairingStatus: jest.fn().mockResolvedValue(mockPairStatus),
    authorizePairingCode: jest.fn().mockResolvedValue(mockPairVerify),
  };

  beforeAll(async () => {
    const moduleFixture: TestingModule = await Test.createTestingModule({
      controllers: [PairingsController],
      providers: [
        {
          provide: PairingsService,
          useValue: mockPairingsService,
        },
      ],
    })
      .overrideGuard(AuthGuard)
      .useValue({
        canActivate: (context: ExecutionContext) => {
          const req = context.switchToHttp().getRequest<Request>();
          req.user = mockUser;
          return true;
        },
      })
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

  describe('PairingsController', () => {
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

    it('/verify (POST)', async () => {
      const payload = { userCode: 'user-code' };
      // eslint-disable-next-line @typescript-eslint/no-unsafe-argument
      const response = await request(app.getHttpServer())
        .post('/auth/pair/verify')
        .send(payload)
        .expect(200);

      expect(response.body).toEqual(mockPairVerify);
      expect(mockPairingsService.authorizePairingCode).toHaveBeenCalledWith(
        payload.userCode,
        mockUser,
      );
    });
  });
});
