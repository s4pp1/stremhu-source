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
import { TorrentsController } from '../torrents.controller';
import { TorrentsService } from '../torrents.service';

// Mocking TorrentsService
jest.mock('../torrents.service', () => ({
  TorrentsService: jest.fn().mockImplementation(() => ({
    updateTorrentClient: jest.fn(),
    find: jest.fn(),
    updateOne: jest.fn(),
    delete: jest.fn(),
  })),
}));

describe('Torrents (Integration)', () => {
  let app: INestApplication;

  const mockTorrent = {
    infoHash: 'mock-hash',
    name: 'mock-torrent',
    isPersisted: true,
  };

  const mockTorrentsService = {
    updateTorrentClient: jest.fn().mockResolvedValue(undefined),
    find: jest.fn().mockResolvedValue([mockTorrent]),
    updateOne: jest.fn().mockResolvedValue(mockTorrent),
    delete: jest.fn().mockResolvedValue(undefined),
  };

  beforeAll(async () => {
    const moduleFixture: TestingModule = await Test.createTestingModule({
      controllers: [TorrentsController],
      providers: [
        {
          provide: TorrentsService,
          useValue: mockTorrentsService,
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

  describe('TorrentsController', () => {
    it('/ (GET)', async () => {
      // eslint-disable-next-line @typescript-eslint/no-unsafe-argument
      const response = await request(app.getHttpServer())
        .get('/torrents')
        .expect(200);

      expect(response.body).toMatchSnapshot();
      expect(mockTorrentsService.find).toHaveBeenCalled();
    });

    it('/:infoHash (PUT)', async () => {
      const payload = { isPersisted: false };
      // eslint-disable-next-line @typescript-eslint/no-unsafe-argument
      const response = await request(app.getHttpServer())
        .put(`/torrents/${mockTorrent.infoHash}`)
        .send(payload)
        .expect(200);

      expect(response.body).toMatchSnapshot();
      expect(mockTorrentsService.updateOne).toHaveBeenCalledWith(
        mockTorrent.infoHash,
        payload,
      );
    });

    it('/:infoHash (DELETE)', async () => {
      // eslint-disable-next-line @typescript-eslint/no-unsafe-argument
      await request(app.getHttpServer())
        .delete(`/torrents/${mockTorrent.infoHash}`)
        .expect(200);

      expect(mockTorrentsService.delete).toHaveBeenCalledWith(
        mockTorrent.infoHash,
      );
    });
  });
});
