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
import { MediaTypeEnum } from 'src/common/enum/media-type.enum';
import { User } from 'src/users/entity/user.entity';
import { UserRoleEnum } from 'src/users/enum/user-role.enum';

import { StremioStreamsController } from '../stremio-streams.controller';
import { StremioStreamsService } from '../stremio-streams.service';

// Mocking StremioStreamsService
jest.mock('../stremio-streams.service', () => ({
  StremioStreamsService: jest.fn().mockImplementation(() => ({
    streams: jest.fn(),
  })),
}));

describe('StremioStreams (Integration)', () => {
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
  const mockStream = {
    title: 'Mock Stream',
    url: 'http://mock-url.com',
  };

  const mockStreamsService = {
    streams: jest.fn().mockResolvedValue([mockStream]),
  };

  beforeAll(async () => {
    const moduleFixture: TestingModule = await Test.createTestingModule({
      controllers: [StremioStreamsController],
      providers: [
        {
          provide: StremioStreamsService,
          useValue: mockStreamsService,
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

  describe('StremioStreamsController', () => {
    it('/:mediaType/:id.json (GET) - Movie', async () => {
      const imdbId = 'tt1234567';
      // eslint-disable-next-line @typescript-eslint/no-unsafe-argument
      const response = await request(app.getHttpServer())
        .get(
          `/${mockToken}/stremio/stream/${MediaTypeEnum.MOVIE}/${imdbId}.json`,
        )
        .expect(200);

      expect(response.body).toEqual({ streams: [mockStream] });
      expect(mockStreamsService.streams).toHaveBeenCalledWith(
        mockUser,
        MediaTypeEnum.MOVIE,
        expect.objectContaining({ imdbId }),
      );
    });

    it('/:mediaType/:id.json (GET) - Series', async () => {
      const imdbId = 'tt1234567:1:1';
      // eslint-disable-next-line @typescript-eslint/no-unsafe-argument
      const response = await request(app.getHttpServer())
        .get(
          `/${mockToken}/stremio/stream/${MediaTypeEnum.SERIES}/${imdbId}.json`,
        )
        .expect(200);

      expect(response.body).toEqual({ streams: [mockStream] });
      expect(mockStreamsService.streams).toHaveBeenCalledWith(
        mockUser,
        MediaTypeEnum.SERIES,
        expect.objectContaining({
          imdbId: 'tt1234567',
          series: { season: 1, episode: 1 },
        }),
      );
    });
  });
});
