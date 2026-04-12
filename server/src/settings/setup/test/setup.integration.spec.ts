import {
  ClassSerializerInterceptor,
  INestApplication,
  ValidationPipe,
} from '@nestjs/common';
import { Reflector } from '@nestjs/core';
import { Test, TestingModule } from '@nestjs/testing';
import { NextFunction, Request, Response } from 'express';
import request from 'supertest';

import { UserRoleEnum } from '../../../users/enum/user-role.enum';
import { SetupController } from '../setup.controller';
import { SetupService } from '../setup.service';

// Mocking SetupService
jest.mock('../setup.service', () => ({
  SetupService: jest.fn().mockImplementation(() => ({
    create: jest.fn(),
    status: jest.fn(),
  })),
}));

describe('Setup (Integration)', () => {
  let app: INestApplication;

  const mockUser = {
    id: '123e4567-e89b-12d3-a456-426614174000',
    username: 'admin',
    userRole: UserRoleEnum.ADMIN,
    token: 'mock-token',
  };

  const mockStatus = {
    isSetup: false,
  };

  const mockSetupService = {
    create: jest.fn().mockResolvedValue(mockUser),
    status: jest.fn().mockResolvedValue(mockStatus),
  };

  beforeAll(async () => {
    const moduleFixture: TestingModule = await Test.createTestingModule({
      controllers: [SetupController],
      providers: [
        {
          provide: SetupService,
          useValue: mockSetupService,
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

    // Mock express-session
    app.use((req: Request, res: Response, next: NextFunction) => {
      // eslint-disable-next-line @typescript-eslint/no-unsafe-member-access
      (req as any).session = {};
      next();
    });

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

  describe('SetupController', () => {
    it('/ (POST)', async () => {
      const payload = {
        username: 'admin',
        password: 'password123',
      };
      // eslint-disable-next-line @typescript-eslint/no-unsafe-argument
      const response = await request(app.getHttpServer())
        .post('/settings/setup')
        .send(payload)
        .expect(201);

      expect(response.body).toMatchSnapshot();
      expect(mockSetupService.create).toHaveBeenCalledWith(payload);
    });

    it('/status (GET)', async () => {
      // eslint-disable-next-line @typescript-eslint/no-unsafe-argument
      const response = await request(app.getHttpServer())
        .get('/settings/setup/status')
        .expect(200);

      expect(response.body).toEqual(mockStatus);
      expect(mockSetupService.status).toHaveBeenCalled();
    });
  });
});
