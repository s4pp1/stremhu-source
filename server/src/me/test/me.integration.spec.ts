import {
  ClassSerializerInterceptor,
  INestApplication,
  ValidationPipe,
} from '@nestjs/common';
import { Reflector } from '@nestjs/core';
import { Test, TestingModule } from '@nestjs/testing';
import { NextFunction, Request, Response } from 'express';
import request from 'supertest';

import { AuthGuard } from '../../auth/guards/auth.guard';
import { User } from '../../users/entity/user.entity';
import { UserRoleEnum } from '../../users/enum/user-role.enum';
import { UserPreferencesService } from '../../users/preferences/user-preferences.service';
import { UsersService } from '../../users/users.service';
import { MeController } from '../me.controller';

// Mocking UsersService
jest.mock('../../users/users.service', () => ({
  UsersService: jest.fn().mockImplementation(() => ({
    updateOrThrow: jest.fn(),
    regenerateToken: jest.fn(),
  })),
}));

// Mocking UserPreferencesService
jest.mock('../../users/preferences/user-preferences.service', () => ({
  UserPreferencesService: jest.fn().mockImplementation(() => ({
    find: jest.fn(),
  })),
}));

describe('Me (Integration)', () => {
  let app: INestApplication;

  const mockUserId = '123e4567-e89b-12d3-a456-426614174000';
  const mockUser: User = {
    id: mockUserId,
    username: 'testuser',
    passwordHash: null,
    token: 'mock-token',
    userRole: UserRoleEnum.USER,
    torrentSeed: null,
    onlyBestTorrent: false,
    updatedAt: new Date('2026-04-12T10:00:00Z'),
    createdAt: new Date('2026-04-12T10:00:00Z'),
  };

  const mockUsersService = {
    updateOrThrow: jest.fn().mockResolvedValue(mockUser),
    regenerateToken: jest.fn().mockResolvedValue(mockUser),
  };

  const mockUserPreferencesService = {
    find: jest.fn().mockResolvedValue([]),
  };

  beforeAll(async () => {
    const moduleFixture: TestingModule = await Test.createTestingModule({
      controllers: [MeController],
      providers: [
        {
          provide: UsersService,
          useValue: mockUsersService,
        },
        {
          provide: UserPreferencesService,
          useValue: mockUserPreferencesService,
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

    app.use((req: Request, res: Response, next: NextFunction) => {
      req.user = mockUser;
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

  describe('MeController', () => {
    it('/ (GET)', async () => {
      // eslint-disable-next-line @typescript-eslint/no-unsafe-argument
      const response = await request(app.getHttpServer())
        .get('/me')
        .expect(200);

      expect(response.body).toMatchSnapshot();
    });

    it('/ (PUT)', async () => {
      const payload = { username: 'updateduser' };
      // eslint-disable-next-line @typescript-eslint/no-unsafe-argument
      const response = await request(app.getHttpServer())
        .put('/me')
        .send(payload)
        .expect(200);

      expect(response.body).toMatchSnapshot();
      expect(mockUsersService.updateOrThrow).toHaveBeenCalledWith(
        mockUserId,
        payload,
      );
    });

    it('/token/regenerate (PUT)', async () => {
      // eslint-disable-next-line @typescript-eslint/no-unsafe-argument
      const response = await request(app.getHttpServer())
        .put('/me/token/regenerate')
        .expect(200);

      expect(response.body).toMatchSnapshot();
      expect(mockUsersService.regenerateToken).toHaveBeenCalledWith(mockUserId);
    });
  });
});
