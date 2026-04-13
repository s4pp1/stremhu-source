import {
  ClassSerializerInterceptor,
  INestApplication,
  ValidationPipe,
} from '@nestjs/common';
import { Reflector } from '@nestjs/core';
import { Test, TestingModule } from '@nestjs/testing';
import request from 'supertest';

import { AuthGuard } from '../../../../auth/guards/auth.guard';
import { RolesGuard } from '../../../../auth/guards/roles.guard';
import { SettingsCoreService } from '../../../../settings/core/settings-core.service';
import { RelayCoreService } from '../../../core/relay-core.service';
import { RelaySettingsInternalController } from '../relay-settings-internal.controller';

// Mocking RelayCoreService
jest.mock('../../../core/relay-core.service', () => ({
  RelayCoreService: jest.fn().mockImplementation(() => ({
    updateConfig: jest.fn(),
  })),
}));

// Mocking SettingsCoreService
jest.mock('../../../../settings/core/settings-core.service', () => ({
  SettingsCoreService: jest.fn().mockImplementation(() => ({
    relaySettings: jest.fn(),
    updateRelaySettings: jest.fn(),
  })),
}));

describe('RelaySettingsInternal (Integration)', () => {
  let app: INestApplication;

  const mockRelaySettings = {
    port: 6881,
    downloadLimit: 0,
  };

  const mockRelayCoreService = {
    updateConfig: jest.fn().mockResolvedValue(undefined),
  };

  const mockSettingsCoreService = {
    relaySettings: jest.fn().mockResolvedValue(mockRelaySettings),
    updateRelaySettings: jest.fn().mockResolvedValue(mockRelaySettings),
  };

  beforeAll(async () => {
    const moduleFixture: TestingModule = await Test.createTestingModule({
      controllers: [RelaySettingsInternalController],
      providers: [
        {
          provide: RelayCoreService,
          useValue: mockRelayCoreService,
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

  describe('RelaySettingsInternalController', () => {
    it('/ (GET)', async () => {
      // eslint-disable-next-line @typescript-eslint/no-unsafe-argument
      const response = await request(app.getHttpServer())
        .get('/relay/settings')
        .expect(200);

      expect(response.body).toEqual(mockRelaySettings);
      expect(mockSettingsCoreService.relaySettings).toHaveBeenCalled();
    });

    it('/ (PUT)', async () => {
      const payload = { port: 1234 };
      // eslint-disable-next-line @typescript-eslint/no-unsafe-argument
      const response = await request(app.getHttpServer())
        .put('/relay/settings')
        .send(payload)
        .expect(200);

      expect(response.body).toEqual(mockRelaySettings);
      expect(mockSettingsCoreService.updateRelaySettings).toHaveBeenCalledWith(
        expect.objectContaining(payload),
      );
      expect(mockRelayCoreService.updateConfig).toHaveBeenCalledWith(
        mockRelaySettings,
      );
    });
  });
});
