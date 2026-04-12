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
import { RolesGuard } from '../../auth/guards/roles.guard';
import { UsersStore } from '../core/users.store';
import { UserDto } from '../dto/user.dto';
import { User } from '../entity/user.entity';
import { UserRoleEnum } from '../enum/user-role.enum';
import { UsersController } from '../users.controller';
import { UsersService } from '../users.service';

// Mocking UsersService
jest.mock('../users.service', () => ({
  UsersService: jest.fn().mockImplementation(() => ({
    create: jest.fn(),
    updateOrThrow: jest.fn(),
    regenerateToken: jest.fn(),
    deleteOrThrow: jest.fn(),
  })),
}));

// Mocking UsersStore
jest.mock('../core/users.store', () => ({
  UsersStore: jest.fn().mockImplementation(() => ({
    find: jest.fn(),
    findOneByIdOrThrow: jest.fn(),
  })),
}));

describe('Users (Integration)', () => {
  let app: INestApplication;

  const mockAdminId = '123e4567-e89b-12d3-a456-426614174001';
  const mockUserId = '123e4567-e89b-12d3-a456-426614174000';

  const mockUser: UserDto = {
    id: mockUserId,
    username: 'testuser',
    token: 'mock-token',
    userRole: UserRoleEnum.USER,
    torrentSeed: null,
    onlyBestTorrent: false,
    updatedAt: new Date('2026-04-12T10:00:00Z'),
    createdAt: new Date('2026-04-12T10:00:00Z'),
  };

  const mockAdmin: User = {
    id: mockAdminId,
    username: 'admin',
    passwordHash: null,
    token: 'admin-token',
    userRole: UserRoleEnum.ADMIN,
    torrentSeed: null,
    onlyBestTorrent: false,
    updatedAt: new Date('2026-04-12T10:00:00Z'),
    createdAt: new Date('2026-04-12T10:00:00Z'),
  };

  const mockUsersService = {
    create: jest.fn().mockResolvedValue(mockUser),
    updateOrThrow: jest.fn().mockResolvedValue(mockUser),
    regenerateToken: jest.fn().mockResolvedValue(mockUser),
    deleteOrThrow: jest.fn().mockResolvedValue(undefined),
  };

  const mockUsersStore = {
    find: jest.fn().mockResolvedValue([mockUser]),
    findOneByIdOrThrow: jest.fn().mockResolvedValue(mockUser),
  };

  beforeAll(async () => {
    const moduleFixture: TestingModule = await Test.createTestingModule({
      controllers: [UsersController],
      providers: [
        {
          provide: UsersService,
          useValue: mockUsersService,
        },
        {
          provide: UsersStore,
          useValue: mockUsersStore,
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

    app.use((req: Request, res: Response, next: NextFunction) => {
      req.user = mockAdmin;
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

  describe('UsersController', () => {
    it('/ (POST)', async () => {
      const payload = {
        username: 'newuser',
        password: 'password123',
      };
      // eslint-disable-next-line @typescript-eslint/no-unsafe-argument
      const response = await request(app.getHttpServer())
        .post('/users')
        .send(payload)
        .expect(201);

      expect(response.body).toMatchSnapshot();
      expect(mockUsersService.create).toHaveBeenCalled();
    });

    it('/ (GET)', async () => {
      // eslint-disable-next-line @typescript-eslint/no-unsafe-argument
      const response = await request(app.getHttpServer())
        .get('/users')
        .expect(200);

      expect(response.body).toMatchSnapshot();
      expect(mockUsersStore.find).toHaveBeenCalled();
    });

    it('/:userId (GET)', async () => {
      // eslint-disable-next-line @typescript-eslint/no-unsafe-argument
      const response = await request(app.getHttpServer())
        .get(`/users/${mockUserId}`)
        .expect(200);

      expect(response.body).toMatchSnapshot();
      expect(mockUsersStore.findOneByIdOrThrow).toHaveBeenCalledWith(
        mockUserId,
      );
    });

    it('/:userId (PUT)', async () => {
      const payload = { username: 'updateduser' };
      // eslint-disable-next-line @typescript-eslint/no-unsafe-argument
      const response = await request(app.getHttpServer())
        .put(`/users/${mockUserId}`)
        .send(payload)
        .expect(200);

      expect(response.body).toMatchSnapshot();
      expect(mockUsersService.updateOrThrow).toHaveBeenCalledWith(
        mockUserId,
        payload,
      );
    });

    it('/:userId/token/regenerate (PUT)', async () => {
      // eslint-disable-next-line @typescript-eslint/no-unsafe-argument
      const response = await request(app.getHttpServer())
        .put(`/users/${mockUserId}/token/regenerate`)
        .expect(200);

      expect(response.body).toMatchSnapshot();
      expect(mockUsersService.regenerateToken).toHaveBeenCalledWith(mockUserId);
    });

    it('/:userId (DELETE)', async () => {
      // eslint-disable-next-line @typescript-eslint/no-unsafe-argument
      await request(app.getHttpServer())
        .delete(`/users/${mockUserId}`)
        .expect(200);

      expect(mockUsersService.deleteOrThrow).toHaveBeenCalledWith(mockUserId);
    });

    it('/:userId (DELETE) - self deletion forbidden', async () => {
      // eslint-disable-next-line @typescript-eslint/no-unsafe-argument
      await request(app.getHttpServer())
        .delete(`/users/${mockAdminId}`)
        .expect(403);
    });
  });
});
