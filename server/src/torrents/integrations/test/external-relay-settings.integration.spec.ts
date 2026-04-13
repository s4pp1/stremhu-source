import {
  ClassSerializerInterceptor,
  INestApplication,
  ValidationPipe,
} from '@nestjs/common';
import { Reflector } from '@nestjs/core';
import { Test, TestingModule } from '@nestjs/testing';
import request from 'supertest';

import { RolesGuard } from '../../../auth/guards/roles.guard';
import { TokenGuard } from '../../../auth/guards/token.guard';
import { SettingsCoreService } from '../../../settings/core/settings-core.service';
import { TorrentsService } from '../../torrents.service';
import { ExternalRelaySettingsController } from '../external-relay-settings.controller';

// Mocking SettingsCoreService
jest.mock('../../../settings/core/settings-core.service', () => ({
  SettingsCoreService: jest.fn().mockImplementation(() => ({
    updateRelaySettings: jest.fn(),
  })),
}));

// Mocking TorrentsService
jest.mock('../../torrents.service', () => ({
  TorrentsService: jest.fn().mockImplementation(() => ({
    updateTorrentClient: jest.fn(),
  })),
}));

describe('ExternalRelaySettings (Integration)', () => {
  let app: INestApplication;

  const mockToken = 'mock-token';
  const mockRelaySettings = {
    port: 6881,
    downloadLimit: 0,
  };

  const mockSettingsCoreService = {
    updateRelaySettings: jest.fn().mockResolvedValue(mockRelaySettings),
  };

  const mockTorrentsService = {
    updateTorrentClient: jest.fn().mockResolvedValue(undefined),
  };

  beforeAll(async () => {
    const moduleFixture: TestingModule = await Test.createTestingModule({
      controllers: [ExternalRelaySettingsController],
      providers: [
        {
          provide: SettingsCoreService,
          useValue: mockSettingsCoreService,
        },
        {
          provide: TorrentsService,
          useValue: mockTorrentsService,
        },
      ],
    })
      .overrideGuard(TokenGuard)
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

  describe('ExternalRelaySettingsController', () => {
    it('/:token/external/relay/settings (PUT)', async () => {
      const payload = { port: 1234 };
      // eslint-disable-next-line @typescript-eslint/no-unsafe-argument
      await request(app.getHttpServer())
        .put(`/${mockToken}/external/relay/settings`)
        .send(payload)
        .expect(200);

      expect(mockSettingsCoreService.updateRelaySettings).toHaveBeenCalledWith(
        expect.objectContaining(payload),
      );
      expect(mockTorrentsService.updateTorrentClient).toHaveBeenCalledWith(
        mockRelaySettings,
      );
    });
  });
});
