import {
  ClassSerializerInterceptor,
  INestApplication,
  ValidationPipe,
} from '@nestjs/common';
import { Reflector } from '@nestjs/core';
import { Test, TestingModule } from '@nestjs/testing';
import request from 'supertest';

import { TokenGuard } from '../../../auth/guards/token.guard';
import { MediaTypeEnum } from '../../../common/enum/media-type.enum';
import { SEARCH_ID } from '../../stremio.constants';
import { StremioCatalogsController } from '../stremio-catalogs.controller';
import { StremioCatalogsService } from '../stremio-catalogs.service';

// Mocking StremioCatalogsService
jest.mock('../stremio-catalogs.service', () => ({
  StremioCatalogsService: jest.fn().mockImplementation(() => ({
    getMetas: jest.fn(),
    getMeta: jest.fn(),
  })),
}));

describe('StremioCatalogs (Integration)', () => {
  let app: INestApplication;

  const mockToken = 'mock-token';
  const mockMetaPreview = {
    id: 'mock-id',
    name: 'Mock Movie',
  };
  const mockMeta = {
    id: 'mock-id',
    name: 'Mock Movie',
    type: 'movie',
  };

  const mockStremioCatalogService = {
    getMetas: jest.fn().mockResolvedValue([mockMetaPreview]),
    getMeta: jest.fn().mockResolvedValue(mockMeta),
  };

  beforeAll(async () => {
    const moduleFixture: TestingModule = await Test.createTestingModule({
      controllers: [StremioCatalogsController],
      providers: [
        {
          provide: StremioCatalogsService,
          useValue: mockStremioCatalogService,
        },
      ],
    })
      .overrideGuard(TokenGuard)
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

  describe('StremioCatalogsController', () => {
    it('/catalog/:mediaType/:catalogId.json (GET) - Search', async () => {
      const extra = 'search=t-mocktorrentid';
      // eslint-disable-next-line @typescript-eslint/no-unsafe-argument
      const response = await request(app.getHttpServer())
        .get(
          `/${mockToken}/stremio/catalog/${MediaTypeEnum.MOVIE}/${SEARCH_ID}/${extra}.json`,
        )
        .expect(200);

      expect(response.body).toEqual({ metas: [mockMetaPreview] });
      expect(mockStremioCatalogService.getMetas).toHaveBeenCalledWith(
        'mocktorrentid',
      );
    });

    it('/meta/:mediaType/:id.json (GET)', async () => {
      const id = 'ncore:mocktorrentid';
      // eslint-disable-next-line @typescript-eslint/no-unsafe-argument
      const response = await request(app.getHttpServer())
        .get(`/${mockToken}/stremio/meta/${MediaTypeEnum.MOVIE}/${id}.json`)
        .expect(200);

      expect(response.body).toEqual({ meta: mockMeta });
      expect(mockStremioCatalogService.getMeta).toHaveBeenCalledWith(
        'ncore',
        'mocktorrentid',
      );
    });
  });
});
