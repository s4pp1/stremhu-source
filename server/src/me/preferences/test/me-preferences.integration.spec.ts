import {
  ClassSerializerInterceptor,
  INestApplication,
  ValidationPipe,
} from '@nestjs/common';
import { Reflector } from '@nestjs/core';
import { Test, TestingModule } from '@nestjs/testing';
import { NextFunction, Request, Response } from 'express';
import request from 'supertest';

import { AuthGuard } from '../../../auth/guards/auth.guard';
import { PreferenceEnum } from '../../../preferences/enum/preference.enum';
import { User } from '../../../users/entity/user.entity';
import { UserRoleEnum } from '../../../users/enum/user-role.enum';
import { UserPreferencesService } from '../../../users/preferences/user-preferences.service';
import { MePreferencesController } from '../me-preferences.controller';

// Mocking UserPreferencesService
jest.mock('../../../users/preferences/user-preferences.service', () => ({
  UserPreferencesService: jest.fn().mockImplementation(() => ({
    create: jest.fn(),
    find: jest.fn(),
    reorder: jest.fn(),
    findOneByPreferenceOrThrow: jest.fn(),
    updateOne: jest.fn(),
    deleteByPreference: jest.fn(),
  })),
}));

describe('MePreferences (Integration)', () => {
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
  const mockUserPreference = {
    userId: mockUserId,
    preference: PreferenceEnum.LANGUAGE,
    preferred: ['hu'],
    blocked: [],
    order: 0,
  };

  const mockUserPreferencesService = {
    create: jest.fn().mockResolvedValue(mockUserPreference),
    find: jest.fn().mockResolvedValue([mockUserPreference]),
    reorder: jest.fn().mockResolvedValue([mockUserPreference]),
    findOneByPreferenceOrThrow: jest.fn().mockResolvedValue(mockUserPreference),
    updateOne: jest.fn().mockResolvedValue(mockUserPreference),
    deleteByPreference: jest.fn().mockResolvedValue(undefined),
  };

  beforeAll(async () => {
    const moduleFixture: TestingModule = await Test.createTestingModule({
      controllers: [MePreferencesController],
      providers: [
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

  describe('MePreferencesController', () => {
    it('/ (POST)', async () => {
      const payload = {
        preference: PreferenceEnum.LANGUAGE,
        preferred: ['hu'],
        blocked: [],
      };
      // eslint-disable-next-line @typescript-eslint/no-unsafe-argument
      const response = await request(app.getHttpServer())
        .post('/me/preference')
        .send(payload)
        .expect(201);

      expect(response.body).toMatchSnapshot();
      expect(mockUserPreferencesService.create).toHaveBeenCalledWith(
        mockUserId,
        payload,
      );
    });

    it('/ (GET)', async () => {
      // eslint-disable-next-line @typescript-eslint/no-unsafe-argument
      const response = await request(app.getHttpServer())
        .get('/me/preference')
        .expect(200);

      expect(response.body).toMatchSnapshot();
      expect(mockUserPreferencesService.find).toHaveBeenCalledWith(mockUserId);
    });

    it('/reorder (POST)', async () => {
      const payload = { preferences: [PreferenceEnum.LANGUAGE] };
      // eslint-disable-next-line @typescript-eslint/no-unsafe-argument
      const response = await request(app.getHttpServer())
        .post('/me/preference/reorder')
        .send(payload)
        .expect(201);

      expect(response.body).toMatchSnapshot();
      expect(mockUserPreferencesService.reorder).toHaveBeenCalledWith(
        mockUserId,
        payload.preferences,
      );
    });

    it('/:preference (GET)', async () => {
      // eslint-disable-next-line @typescript-eslint/no-unsafe-argument
      const response = await request(app.getHttpServer())
        .get(`/me/preference/${PreferenceEnum.LANGUAGE}`)
        .expect(200);

      expect(response.body).toMatchSnapshot();
      expect(
        mockUserPreferencesService.findOneByPreferenceOrThrow,
      ).toHaveBeenCalledWith(mockUserId, PreferenceEnum.LANGUAGE);
    });

    it('/:preference (PUT)', async () => {
      const payload = { preferred: ['en'], blocked: [] };
      // eslint-disable-next-line @typescript-eslint/no-unsafe-argument
      const response = await request(app.getHttpServer())
        .put(`/me/preference/${PreferenceEnum.LANGUAGE}`)
        .send(payload)
        .expect(200);

      expect(response.body).toMatchSnapshot();
      expect(mockUserPreferencesService.updateOne).toHaveBeenCalledWith(
        mockUserId,
        PreferenceEnum.LANGUAGE,
        payload,
      );
    });

    it('/:preference (DELETE)', async () => {
      // eslint-disable-next-line @typescript-eslint/no-unsafe-argument
      await request(app.getHttpServer())
        .delete(`/me/preference/${PreferenceEnum.LANGUAGE}`)
        .expect(200);

      expect(
        mockUserPreferencesService.deleteByPreference,
      ).toHaveBeenCalledWith(mockUserId, PreferenceEnum.LANGUAGE);
    });
  });
});
