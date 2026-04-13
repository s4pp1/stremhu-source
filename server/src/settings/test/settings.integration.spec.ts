import {
  ClassSerializerInterceptor,
  INestApplication,
  ValidationPipe,
} from '@nestjs/common';
import { Reflector } from '@nestjs/core';
import { Test, TestingModule } from '@nestjs/testing';
import request from 'supertest';

import { AuthGuard } from '../../auth/guards/auth.guard';
import { RolesGuard } from '../../auth/guards/roles.guard';
import { SettingsCoreService } from '../core/settings-core.service';
import { SettingsController } from '../settings.controller';
import { SettingsSyncService } from '../sync/settings-sync.service';

// Mocking SettingsCoreService
jest.mock('../core/settings-core.service', () => ({
  SettingsCoreService: jest.fn().mockImplementation(() => ({
    appSettings: jest.fn(),
    buildLocalUrl: jest.fn(),
  })),
}));

// Mocking SettingsSyncService
jest.mock('../sync/settings-sync.service', () => ({
  SettingsSyncService: jest.fn().mockImplementation(() => ({
    update: jest.fn(),
  })),
}));

describe('Settings (Integration)', () => {
  let app: INestApplication;

  const mockSettings = {
    address: 'https://localhost:3000',
    tmdbApiKey: 'mock-api-key',
  };

  const mockSettingsSyncService = {
    update: jest.fn().mockResolvedValue(mockSettings),
  };

  const mockSettingsCoreService = {
    appSettings: jest.fn().mockResolvedValue(mockSettings),
    buildLocalUrl: jest.fn().mockReturnValue('http://192.168.1.1:3000'),
  };

  beforeAll(async () => {
    const moduleFixture: TestingModule = await Test.createTestingModule({
      controllers: [SettingsController],
      providers: [
        {
          provide: SettingsSyncService,
          useValue: mockSettingsSyncService,
        },
        {
          provide: SettingsCoreService,
          useValue: mockSettingsCoreService,
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

  describe('SettingsController', () => {
    it('/ (GET)', async () => {
      // eslint-disable-next-line @typescript-eslint/no-unsafe-argument
      const response = await request(app.getHttpServer())
        .get('/settings')
        .expect(200);

      expect(response.body).toEqual(mockSettings);
      expect(mockSettingsCoreService.appSettings).toHaveBeenCalled();
    });

    it('/ (PUT)', async () => {
      const payload = { address: 'https://new-url.com' };
      // eslint-disable-next-line @typescript-eslint/no-unsafe-argument
      const response = await request(app.getHttpServer())
        .put('/settings')
        .send(payload)
        .expect(200);

      expect(response.body).toEqual(mockSettings);
      expect(mockSettingsSyncService.update).toHaveBeenCalledWith(
        expect.objectContaining(payload),
      );
    });

    it('/local-url (POST)', async () => {
      const payload = { ipv4: '192.168.1.1' };
      // eslint-disable-next-line @typescript-eslint/no-unsafe-argument
      const response = await request(app.getHttpServer())
        .post('/settings/local-url')
        .send(payload)
        .expect(201);

      expect(response.body).toEqual({ localUrl: 'http://192.168.1.1:3000' });
      expect(mockSettingsCoreService.buildLocalUrl).toHaveBeenCalledWith(
        payload.ipv4,
      );
    });
  });
});
