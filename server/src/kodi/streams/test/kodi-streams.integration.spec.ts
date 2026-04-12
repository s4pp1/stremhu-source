import {
  ClassSerializerInterceptor,
  ExecutionContext,
  INestApplication,
  ValidationPipe,
} from '@nestjs/common';
import { Reflector } from '@nestjs/core';
import { Test, TestingModule } from '@nestjs/testing';
import { Request } from 'express';
import request from 'supertest';

import { TokenGuard } from 'src/auth/guards/token.guard';
import { User } from 'src/users/entity/user.entity';
import { UserRoleEnum } from 'src/users/enum/user-role.enum';

import { KodiStreamsController } from '../kodi-streams.controller';
import { KodiStreamsService } from '../kodi-streams.service';

// Mocking KodiStreamsService
jest.mock('../kodi-streams.service', () => ({
  KodiStreamsService: jest.fn().mockImplementation(() => ({
    imdbStreams: jest.fn(),
  })),
}));

describe('KodiStreams (Integration)', () => {
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
  const mockKodiStream = {
    title: 'Mock Kodi Stream',
    url: 'http://mock-url.com',
  };

  const mockKodiStreamsService = {
    imdbStreams: jest.fn().mockResolvedValue({ streams: [mockKodiStream] }),
  };

  beforeAll(async () => {
    const moduleFixture: TestingModule = await Test.createTestingModule({
      controllers: [KodiStreamsController],
      providers: [
        {
          provide: KodiStreamsService,
          useValue: mockKodiStreamsService,
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

  describe('KodiStreamsController', () => {
    it('/imdb/:imdbId/streams (GET)', async () => {
      const imdbId = 'tt1234567';
      // eslint-disable-next-line @typescript-eslint/no-unsafe-argument
      const response = await request(app.getHttpServer())
        .get(`/${mockToken}/kodi/imdb/${imdbId}/streams`)
        .expect(200);

      expect(response.body).toEqual({ streams: [mockKodiStream] });
      expect(mockKodiStreamsService.imdbStreams).toHaveBeenCalledWith(
        mockUser,
        imdbId,
        {},
      );
    });
  });
});
