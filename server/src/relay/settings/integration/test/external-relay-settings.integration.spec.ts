import {
  ClassSerializerInterceptor,
  INestApplication,
  ValidationPipe,
} from '@nestjs/common';
import { Reflector } from '@nestjs/core';
import { Test, TestingModule } from '@nestjs/testing';
import request from 'supertest';

import { RolesGuard } from '../../../../auth/guards/roles.guard';
import { TokenGuard } from '../../../../auth/guards/token.guard';
import { SettingsCoreService } from '../../../../settings/core/settings-core.service';
import { RelayCoreService } from '../../../core/relay-core.service';
import { RelaySettingsIntegrationController } from '../relay-settings-integration.controller';

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

describe('ExternalRelaySettings (Integration)', () => {
  let app: INestApplication;

  const mockToken = 'mock-token';
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
      controllers: [RelaySettingsIntegrationController],
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

  describe('RelaySettingsIntegrationController', () => {
    it('/:token/relay/settings (GET)', async () => {
      // eslint-disable-next-line @typescript-eslint/no-unsafe-argument
      const response = await request(app.getHttpServer())
        .get(`/${mockToken}/relay/settings`)
        .expect(200);

      expect(response.body).toEqual(mockRelaySettings);
      expect(mockSettingsCoreService.relaySettings).toHaveBeenCalled();
    });

    it('/:token/relay/settings (PUT)', async () => {
      const payload = { port: 1234 };
      // eslint-disable-next-line @typescript-eslint/no-unsafe-argument
      const response = await request(app.getHttpServer())
        .put(`/${mockToken}/relay/settings`)
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
