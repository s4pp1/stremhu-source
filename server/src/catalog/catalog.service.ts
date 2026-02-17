import {
  BadRequestException,
  Inject,
  Injectable,
  Logger,
} from '@nestjs/common';

import { AppSettingsService } from 'src/settings/app/app-settings.service';

import { CATALOG_CLIENT } from './catalog-client.token';
import { ResolveImdbId, ResolvedImdbId } from './catalog.types';
import { CatalogClient, HealthDto } from './client';

@Injectable()
export class CatalogService {
  private readonly logger = new Logger(CatalogService.name);

  constructor(
    @Inject(CATALOG_CLIENT) private readonly client: CatalogClient,
    private appSettingsService: AppSettingsService,
  ) {}

  async catalogHealthCheck(catalogToken?: string): Promise<HealthDto> {
    let token = catalogToken || null;

    if (!catalogToken) {
      const setting = await this.appSettingsService.get();
      token = setting.catalogToken;
    }

    if (!token) {
      throw new BadRequestException('A StremHU Catalog kulcs nincs beállítva');
    }

    try {
      const healthCheck =
        await this.client.monitoring.healthCheckWithToken(token);

      return healthCheck;
    } catch {
      throw new BadRequestException('A StremHU Catalog kulcs hibás');
    }
  }

  async resolveImdbId(payload: ResolveImdbId): Promise<ResolvedImdbId> {
    const { imdbId, season, episode } = payload;
    if (season === undefined || episode === undefined) return { imdbId };

    if (season !== 0) return { imdbId: payload.imdbId };

    const { catalogToken } = await this.appSettingsService.get();
    if (!catalogToken) return { imdbId };

    try {
      const { episodeImdbId } = await this.client.imdb.resolveSpecial(
        catalogToken,
        {
          episodeNumber: episode,
          imdbId: imdbId,
        },
      );

      return { imdbId: episodeImdbId, originalImdbId: imdbId };
    } catch {
      this.logger.error(
        `🛑 A catalog token nem megfelelő vagy a service nem érhető el.`,
      );
      return { imdbId };
    }
  }
}
