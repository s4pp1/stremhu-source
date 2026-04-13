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

import { AuthGuard } from '../../../auth/guards/auth.guard';
import { User } from '../../../users/entity/user.entity';
import { UserRoleEnum } from '../../../users/enum/user-role.enum';
import { PairingsCoreService } from '../../core/pairings-core.service';
import { PairingsInternalController } from '../pairings-internal.controller';

// Mocking PairingsCoreService
jest.mock('../../core/pairings-core.service', () => ({
  PairingsCoreService: jest.fn().mockImplementation(() => ({
    generatePairingCodes: jest.fn(),
    pollPairingStatus: jest.fn(),
    authorizePairingCode: jest.fn(),
  })),
}));

describe('Pairings Internal (Integration)', () => {
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
  const mockPairVerify = {
    verified: true,
  };

  const mockPairingsService = {
    generatePairingCodes: jest.fn(),
    pollPairingStatus: jest.fn(),
    authorizePairingCode: jest.fn().mockResolvedValue(mockPairVerify),
  };

  beforeAll(async () => {
    const moduleFixture: TestingModule = await Test.createTestingModule({
      controllers: [PairingsInternalController],
      providers: [
        {
          provide: PairingsCoreService,
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

  describe('PairingsInternalController', () => {
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
