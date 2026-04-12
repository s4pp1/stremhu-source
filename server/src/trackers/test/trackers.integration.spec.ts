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
import { TrackersStore } from '../core/trackers.store';
import { TrackerEnum } from '../enum/tracker.enum';
import { TrackerMaintenanceService } from '../tracker-maintenance.service';
import { TrackersController } from '../trackers.controller';
import { TrackersService } from '../trackers.service';

// Mocking TrackersStore
jest.mock('../core/trackers.store', () => ({
  TrackersStore: jest.fn().mockImplementation(() => ({
    find: jest.fn(),
  })),
}));

// Mocking TrackersService
jest.mock('../trackers.service', () => ({
  TrackersService: jest.fn().mockImplementation(() => ({
    login: jest.fn(),
    updateOneOrThrow: jest.fn(),
    delete: jest.fn(),
  })),
}));

// Mocking TrackerMaintenanceService
jest.mock('../tracker-maintenance.service', () => ({
  TrackerMaintenanceService: jest.fn().mockImplementation(() => ({
    runTrackersCleanup: jest.fn(),
  })),
}));

describe('Trackers (Integration)', () => {
  let app: INestApplication;

  const mockTracker = {
    tracker: TrackerEnum.NCORE,
    username: 'testuser',
  };

  const mockTrackersStore = {
    find: jest.fn().mockResolvedValue([mockTracker]),
  };

  const mockTrackersService = {
    login: jest.fn().mockResolvedValue(undefined),
    updateOneOrThrow: jest.fn().mockResolvedValue(mockTracker),
    delete: jest.fn().mockResolvedValue(undefined),
  };

  const mockTrackerMaintenanceService = {
    runTrackersCleanup: jest.fn().mockResolvedValue(undefined),
  };

  beforeAll(async () => {
    const moduleFixture: TestingModule = await Test.createTestingModule({
      controllers: [TrackersController],
      providers: [
        {
          provide: TrackersStore,
          useValue: mockTrackersStore,
        },
        {
          provide: TrackersService,
          useValue: mockTrackersService,
        },
        {
          provide: TrackerMaintenanceService,
          useValue: mockTrackerMaintenanceService,
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

  describe('TrackersController', () => {
    it('/ (POST)', async () => {
      const payload = {
        tracker: TrackerEnum.NCORE,
        username: 'testuser',
        password: 'password123',
      };
      // eslint-disable-next-line @typescript-eslint/no-unsafe-argument
      await request(app.getHttpServer())
        .post('/trackers')
        .send(payload)
        .expect(201);

      const { tracker, ...rest } = payload;
      expect(mockTrackersService.login).toHaveBeenCalledWith(
        tracker,
        expect.objectContaining(rest),
      );
    });

    it('/ (GET)', async () => {
      // eslint-disable-next-line @typescript-eslint/no-unsafe-argument
      const response = await request(app.getHttpServer())
        .get('/trackers')
        .expect(200);

      expect(response.body).toMatchSnapshot();
      expect(mockTrackersStore.find).toHaveBeenCalled();
    });

    it('/cleanup (POST)', async () => {
      // eslint-disable-next-line @typescript-eslint/no-unsafe-argument
      await request(app.getHttpServer()).post('/trackers/cleanup').expect(201);

      expect(
        mockTrackerMaintenanceService.runTrackersCleanup,
      ).toHaveBeenCalled();
    });

    it('/:tracker (PUT)', async () => {
      const payload = { hitAndRun: true };
      // eslint-disable-next-line @typescript-eslint/no-unsafe-argument
      const response = await request(app.getHttpServer())
        .put(`/trackers/${TrackerEnum.NCORE}`)
        .send(payload)
        .expect(200);

      expect(response.body).toMatchSnapshot();
      expect(mockTrackersService.updateOneOrThrow).toHaveBeenCalledWith(
        TrackerEnum.NCORE,
        expect.objectContaining(payload),
      );
    });

    it('/:tracker (DELETE)', async () => {
      // eslint-disable-next-line @typescript-eslint/no-unsafe-argument
      await request(app.getHttpServer())
        .delete(`/trackers/${TrackerEnum.NCORE}`)
        .expect(200);

      expect(mockTrackersService.delete).toHaveBeenCalledWith(
        TrackerEnum.NCORE,
      );
    });
  });
});
