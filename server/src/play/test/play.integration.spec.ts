import {
  ClassSerializerInterceptor,
  ExecutionContext,
  INestApplication,
  ValidationPipe,
} from '@nestjs/common';
import { Reflector } from '@nestjs/core';
import { Test, TestingModule } from '@nestjs/testing';
import { Request, Response } from 'express';
import request from 'supertest';

import { TokenGuard } from '../../auth/guards/token.guard';
import { TrackerEnum } from '../../trackers/enum/tracker.enum';
import { User } from '../../users/entity/user.entity';
import { UserRoleEnum } from '../../users/enum/user-role.enum';
import { PlayController } from '../play.controller';
import { PlayService } from '../play.service';

// Mocking PlayService
jest.mock('../play.service', () => ({
  PlayService: jest.fn().mockImplementation(() => ({
    preparePlay: jest.fn(),
  })),
}));

// Mocking playProxy
jest.mock('../play.proxy', () => ({
  playProxy: jest.fn().mockImplementation((req: Request, res: Response) => {
    // eslint-disable-next-line @typescript-eslint/no-unsafe-call, @typescript-eslint/no-unsafe-member-access
    res.status(200).send('mock-proxy-response');
  }),
}));

describe('Play (Integration)', () => {
  let app: INestApplication;

  const mockToken = 'mock-token';
  const mockUser: User = {
    id: 'user-id',
    username: 'testuser',
    passwordHash: null,
    token: 'mock-token',
    userRole: UserRoleEnum.USER,
    torrentSeed: null,
    onlyBestTorrent: false,
    updatedAt: new Date('2026-04-12T10:00:00Z'),
    createdAt: new Date('2026-04-12T10:00:00Z'),
  };
  const mockRelayTorrent = {
    infoHash: 'mock-info-hash',
  };

  const mockPlayService = {
    preparePlay: jest.fn().mockResolvedValue(mockRelayTorrent),
  };

  beforeAll(async () => {
    const moduleFixture: TestingModule = await Test.createTestingModule({
      controllers: [PlayController],
      providers: [
        {
          provide: PlayService,
          useValue: mockPlayService,
        },
      ],
    })
      .overrideGuard(TokenGuard)
      .useValue({
        canActivate: (context: ExecutionContext) => {
          const req = context.switchToHttp().getRequest<Request>();
          req.user = mockUser;
          return true;
        },
      })
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

  describe('PlayController', () => {
    it('/:tracker/:torrentId/:fileIdx (GET)', async () => {
      const tracker = TrackerEnum.NCORE;
      const torrentId = 'mock-torrent-id';
      const fileIdx = 0;
      // eslint-disable-next-line @typescript-eslint/no-unsafe-argument
      const response = await request(app.getHttpServer())
        .get(`/${mockToken}/play/${tracker}/${torrentId}/${fileIdx}`)
        .expect(200);

      expect(response.text).toBe('mock-proxy-response');
      expect(mockPlayService.preparePlay).toHaveBeenCalledWith({
        tracker,
        torrentId,
      });
    });
  });
});
