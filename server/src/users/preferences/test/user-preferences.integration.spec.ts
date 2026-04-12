import {
  ClassSerializerInterceptor,
  INestApplication,
  ValidationPipe,
} from '@nestjs/common';
import { Reflector } from '@nestjs/core';
import { Test, TestingModule } from '@nestjs/testing';
import request from 'supertest';

import { AuthGuard } from 'src/auth/guards/auth.guard';
import { RolesGuard } from 'src/auth/guards/roles.guard';
import { PreferenceEnum } from 'src/preferences/enum/preference.enum';
import { UserPreferencesService } from 'src/users/preferences/user-preferences.service';

import { UserPreferencesController } from '../user-preferences.controller';

// Mocking UserPreferencesService
jest.mock('src/users/preferences/user-preferences.service', () => ({
  UserPreferencesService: jest.fn().mockImplementation(() => ({
    create: jest.fn(),
    find: jest.fn(),
    reorder: jest.fn(),
    findOneByPreferenceOrThrow: jest.fn(),
    updateOne: jest.fn(),
    deleteByPreference: jest.fn(),
  })),
}));

describe('UserPreferences (Integration)', () => {
  let app: INestApplication;

  const mockUserId = '123e4567-e89b-12d3-a456-426614174000';
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
      controllers: [UserPreferencesController],
      providers: [
        {
          provide: UserPreferencesService,
          useValue: mockUserPreferencesService,
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

  describe('UserPreferencesController', () => {
    it('/ (POST)', async () => {
      const payload = {
        preference: PreferenceEnum.LANGUAGE,
        preferred: ['hu'],
        blocked: [],
      };
      // eslint-disable-next-line @typescript-eslint/no-unsafe-argument
      const response = await request(app.getHttpServer())
        .post(`/users/${mockUserId}/preferences`)
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
        .get(`/users/${mockUserId}/preferences`)
        .expect(200);

      expect(response.body).toMatchSnapshot();
      expect(mockUserPreferencesService.find).toHaveBeenCalledWith(mockUserId);
    });

    it('/reorder (POST)', async () => {
      const payload = { preferences: [PreferenceEnum.LANGUAGE] };
      // eslint-disable-next-line @typescript-eslint/no-unsafe-argument
      const response = await request(app.getHttpServer())
        .post(`/users/${mockUserId}/preferences/reorder`)
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
        .get(`/users/${mockUserId}/preferences/${PreferenceEnum.LANGUAGE}`)
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
        .put(`/users/${mockUserId}/preferences/${PreferenceEnum.LANGUAGE}`)
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
        .delete(`/users/${mockUserId}/preferences/${PreferenceEnum.LANGUAGE}`)
        .expect(200);

      expect(
        mockUserPreferencesService.deleteByPreference,
      ).toHaveBeenCalledWith(mockUserId, PreferenceEnum.LANGUAGE);
    });
  });
});
