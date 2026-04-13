import {
  BadRequestException,
  Injectable,
  Logger,
  OnModuleInit,
} from '@nestjs/common';
import { ConfigService } from '@nestjs/config';

import { SettingsCoreService } from 'src/settings/core/settings-core.service';

import { ResolveImdbId, ResolvedImdbId } from './catalog.types';
import {
  HealthDto,
  imdbResolverResolveSpecial,
  monitoringHealthCheckWithToken,
} from './client/catalog-client';
import { CATALOG_AXIOS_INSTANCE } from './client/catalog-client-instance';

@Injectable()
export class CatalogService implements OnModuleInit {
  private readonly logger = new Logger(CatalogService.name);

  constructor(
    private settingsCoreService: SettingsCoreService,
    private configService: ConfigService,
  ) {}

  onModuleInit() {
    CATALOG_AXIOS_INSTANCE.defaults.baseURL =
      this.configService.getOrThrow<string>('app.stremhu-catalog-url');
  }

  async catalogHealthCheck(catalogToken?: string): Promise<HealthDto> {
    let token = catalogToken || null;

    if (!catalogToken) {
      const setting = await this.settingsCoreService.appSettings();
      token = setting.catalogToken;
    }

    if (!token) {
      throw new BadRequestException('A StremHU Catalog kulcs nincs beállítva');
    }

    try {
      const healthCheck = await monitoringHealthCheckWithToken(token);

      return healthCheck;
    } catch {
      throw new BadRequestException('A StremHU Catalog kulcs hibás');
    }
  }

  async resolveImdbId(payload: ResolveImdbId): Promise<ResolvedImdbId> {
    const { imdbId, season, episode } = payload;
    if (season === undefined || episode === undefined) return { imdbId };

    if (season !== 0) return { imdbId: payload.imdbId };

    const { catalogToken } = await this.settingsCoreService.appSettings();
    if (!catalogToken) return { imdbId };

    try {
      const { episodeImdbId } = await imdbResolverResolveSpecial(catalogToken, {
        episodeNumber: episode,
        imdbId: imdbId,
      });

      return { imdbId: episodeImdbId, originalImdbId: imdbId };
    } catch {
      this.logger.error(
        `🛑 A catalog token nem megfelelő vagy a service nem érhető el.`,
      );
      return { imdbId };
    }
  }
}
