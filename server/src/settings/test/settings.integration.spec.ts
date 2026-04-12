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
import { AppSettingsService } from '../app/app-settings.service';
import { SettingsController } from '../settings.controller';
import { SettingsService } from '../settings.service';

// Mocking SettingsService
jest.mock('../settings.service', () => ({
  SettingsService: jest.fn().mockImplementation(() => ({
    update: jest.fn(),
    buildLocalUrl: jest.fn(),
  })),
}));

// Mocking AppSettingsService
jest.mock('../app/app-settings.service', () => ({
  AppSettingsService: jest.fn().mockImplementation(() => ({
    get: jest.fn(),
  })),
}));

describe('Settings (Integration)', () => {
  let app: INestApplication;

  const mockSettings = {
    address: 'https://localhost:3000',
    tmdbApiKey: 'mock-api-key',
  };

  const mockSettingsService = {
    update: jest.fn().mockResolvedValue(mockSettings),
    buildLocalUrl: jest.fn().mockReturnValue('http://192.168.1.1:3000'),
  };

  const mockAppSettingsService = {
    get: jest.fn().mockResolvedValue(mockSettings),
  };

  beforeAll(async () => {
    const moduleFixture: TestingModule = await Test.createTestingModule({
      controllers: [SettingsController],
      providers: [
        {
          provide: SettingsService,
          useValue: mockSettingsService,
        },
        {
          provide: AppSettingsService,
          useValue: mockAppSettingsService,
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
      expect(mockAppSettingsService.get).toHaveBeenCalled();
    });

    it('/ (PUT)', async () => {
      const payload = { address: 'https://new-url.com' };
      // eslint-disable-next-line @typescript-eslint/no-unsafe-argument
      const response = await request(app.getHttpServer())
        .put('/settings')
        .send(payload)
        .expect(200);

      expect(response.body).toEqual(mockSettings);
      expect(mockSettingsService.update).toHaveBeenCalledWith(
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
      expect(mockSettingsService.buildLocalUrl).toHaveBeenCalledWith(
        payload.ipv4,
      );
    });
  });
});
