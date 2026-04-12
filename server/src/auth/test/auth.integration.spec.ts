import {
  ClassSerializerInterceptor,
  INestApplication,
  ValidationPipe,
} from '@nestjs/common';
import { Reflector } from '@nestjs/core';
import { Test, TestingModule } from '@nestjs/testing';
import { NextFunction, Request, Response } from 'express';
import request from 'supertest';

import { UserRoleEnum } from '../../users/enum/user-role.enum';
import { AuthController } from '../auth.controller';
import { AuthService } from '../auth.service';
import { AuthGuard } from '../guards/auth.guard';

// Mocking AuthService
jest.mock('../auth.service', () => ({
  AuthService: jest.fn().mockImplementation(() => ({
    validate: jest.fn(),
  })),
}));

describe('Auth (Integration)', () => {
  let app: INestApplication;

  const mockUserId = '123e4567-e89b-12d3-a456-426614174000';
  const mockUser = {
    id: mockUserId,
    username: 'testuser',
    userRole: UserRoleEnum.USER,
    token: 'mock-token',
  };

  const mockAuthService = {
    validate: jest.fn().mockResolvedValue(mockUser),
  };

  beforeAll(async () => {
    const moduleFixture: TestingModule = await Test.createTestingModule({
      controllers: [AuthController],
      providers: [
        {
          provide: AuthService,
          useValue: mockAuthService,
        },
      ],
    })
      .overrideGuard(AuthGuard)
      .useValue({ canActivate: () => true })
      .compile();

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
      (req as any).session = {
        userId: null,
        destroy: jest
          .fn()
          .mockImplementation((cb: (err?: any) => void) => cb()),
      };
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

  describe('AuthController', () => {
    it('/login (POST)', async () => {
      const payload = {
        username: 'testuser',
        password: 'password123',
      };
      // eslint-disable-next-line @typescript-eslint/no-unsafe-argument
      const response = await request(app.getHttpServer())
        .post('/auth/login')
        .send(payload)
        .expect(201);

      expect(response.body).toMatchSnapshot();
      expect(mockAuthService.validate).toHaveBeenCalledWith(
        payload.username,
        payload.password,
      );
    });

    it('/logout (POST)', async () => {
      // eslint-disable-next-line @typescript-eslint/no-unsafe-argument
      await request(app.getHttpServer()).post('/auth/logout').expect(200);
    });
  });
});
